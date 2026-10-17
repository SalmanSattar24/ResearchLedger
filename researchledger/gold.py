"""Find candidate gold ranges for an evaluation set by plain text search, independent of the retriever.

Gold ranges are meant to list every current passage that states an item's fact. This module proposes additional
ranges for a person to review; it never edits an evaluation set.

How a passage is matched, with no ranking model involved:
- passages are paragraphs (blank-line blocks within a section), and single rows for Markdown tables;
- archived paths (CorpusConfig.archived) are never proposed;
- a passage matches one `must_include` fact if it contains every number in the fact (exact, digit-bounded) and
  at least half of the fact's distinctive words (four or more letters, not a stopword), matched on a five-letter
  prefix so that 'withdrawn' and 'withdrawal' agree. A fact with no numbers needs at least two distinctive words;
- passages already overlapping a gold range are left out.
Using the retriever's own hits as candidates would make the widened gold favour the retriever, so it is not used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .chunking import _blocks, sections
from .corpus import CorpusConfig, GitSource
from .documents import UnsupportedDocument, document_lines
from .leakage import is_allowed, scan_lines
from .retrieve import _STOPWORDS
from .tables import _SEPARATOR

_NUM = re.compile(r"\d+(?:\.\d+)?(?:e-?\d+)?")
_WORD = re.compile(r"[a-z][a-z\-]{3,}")
_GENERIC = frozenset(
    "about after also been before both from into more most only over same some such than them then there these "
    "they this those under until very were what when where which while with would".split()
)


def _norm(s: str) -> str:
    for ch in ("‑", "‐", "–", "—", "−"):
        s = s.replace(ch, "-")
    return s.replace(",", "").replace("≈", "").lower()


@dataclass(frozen=True)
class Passage:
    path: str
    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class Fact:
    text: str
    numbers: frozenset[str]
    words: frozenset[str]  # five-letter prefixes

    @classmethod
    def parse(cls, text: str) -> Fact:
        t = _norm(text)
        words = {w[:5] for w in _WORD.findall(t) if w not in _STOPWORDS and w not in _GENERIC}
        return cls(text, frozenset(_NUM.findall(t)), frozenset(words))

    def matches(self, passage_text: str) -> bool:
        t = _norm(passage_text)
        if not all(re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", t) for n in self.numbers):
            return False
        present = {w[:5] for w in _WORD.findall(t)}
        hit = len(self.words & present)
        if not self.numbers:
            return hit >= 2 and hit >= len(self.words) / 2
        return hit >= len(self.words) / 2


def passages(config: CorpusConfig, source: GitSource | None = None) -> list[Passage]:
    source = source or GitSource(config)
    out: list[Passage] = []
    for path in source.list_files():
        if not is_allowed(path) or config.is_archived(path):
            continue
        try:
            lines = scan_lines(path, document_lines(path, source.read(path))).lines
        except UnsupportedDocument:
            continue
        for _, section in sections(path, lines):
            for block in _blocks(section):
                is_table = len(block) >= 3 and block[0][1].lstrip().startswith("|") and _SEPARATOR.match(block[1][1])
                if is_table:
                    out += [Passage(path, n, n, s) for n, s in block[2:]]
                else:
                    out.append(Passage(path, block[0][0], block[-1][0], "\n".join(s for _, s in block)))
    return out


def candidates(config: CorpusConfig, questions_path: str | Path, max_per_item: int = 6) -> list[dict]:
    qs = yaml.safe_load(Path(questions_path).read_text(encoding="utf-8"))
    pool = passages(config)
    report = []
    for it in qs["items"]:
        if it["type"] == "safety":
            continue
        gold = [(qs["files"][g["f"]], g["lines"][0], g["lines"][1]) for g in it["gold"]]
        facts = [Fact.parse(f) for f in it["must_include"]]
        found = []
        for p in pool:
            if any(p.path == g and p.start_line <= e and p.end_line >= s for g, s, e in gold):
                continue
            matched = [i for i, f in enumerate(facts) if f.matches(p.text)]
            if matched:
                found.append((len(matched), p, matched))
        found.sort(key=lambda x: (-x[0], x[1].path, x[1].start_line))
        report.append({
            "id": it["id"],
            "type": it["type"],
            "q": it["q"],
            "facts": it["must_include"],
            "gold": [f"{g}:{s}-{e}" for g, s, e in gold],
            "candidates": [
                {"range": f"{p.path}:{p.start_line}-{p.end_line}", "facts_matched": [i + 1 for i in m],
                 "excerpt": " ".join(p.text.split())[:220]}
                for _, p, m in found[:max_per_item]
            ],
            "more": max(0, len(found) - max_per_item),
        })
    return report


def to_markdown(corpus: str, report: list[dict]) -> str:
    out = [f"# Gold-range candidates: {corpus}", "",
           "Proposed by plain text search (researchledger/gold.py). Nothing here changes the evaluation set.", ""]
    for r in report:
        out.append(f"## {r['id']} ({r['type']}): {r['q']}")
        out.append("Facts: " + "; ".join(f"[{i}] {f}" for i, f in enumerate(r["facts"], 1)))
        out.append("Current gold: " + ", ".join(r["gold"]))
        if not r["candidates"]:
            out.append("Candidates: none")
        for c in r["candidates"]:
            out.append(f"- `{c['range']}` matches facts {c['facts_matched']}: {c['excerpt']}")
        if r["more"]:
            out.append(f"- ... {r['more']} more weaker matches not shown")
        out.append("")
    return "\n".join(out)
