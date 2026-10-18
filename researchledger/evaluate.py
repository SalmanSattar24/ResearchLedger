"""Retrieval evaluation against an evaluation set's gold line ranges.

For each non-safety item: does any of the top-k retrieved chunks overlap a gold range (same file, overlapping
lines)? This is the retrieval-side bound on the "citation recall" gate in eval/THRESHOLDS.md: an answer can only
cite lines that retrieval surfaced. Safety items have no gold lines and are skipped here.

A second, diagnostic measure, evidence@k, asks whether the top-k chunks contain every number in the item's
`must_include` facts, wherever they come from. Research records often state one fact in several documents, and
gold ranges list only some of them, so recall@k alone undercounts retrieval that found the fact elsewhere.
Items whose facts contain no numbers are left out of evidence@k.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .retrieve import BM25Index, Hit

KS = (1, 3, 5, 10)
_NUM = re.compile(r"\d+(?:\.\d+)?(?:e-?\d+)?")


def _norm(s: str) -> str:
    return s.replace("\u2011", "-").replace("\u2013", "-").replace("\u2212", "-").replace(",", "")


def evidence_rank(hits: list[Hit], facts: list[str]) -> int | None:
    """Smallest k such that the top-k chunks together contain every number in the facts (None if never)."""
    numbers = {n for f in facts for n in _NUM.findall(_norm(f))}
    if not numbers:
        return None
    seen = ""
    for k, h in enumerate(hits, 1):
        seen += _norm(h.text) + "\n"
        if all(re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", seen) for n in numbers):
            return k
    return None


def overlaps(hit: Hit, path: str, start: int, end: int) -> bool:
    return hit.path == path and hit.start_line <= end and hit.end_line >= start


def evaluate_retrieval(index_path: str | Path, questions_path: str | Path, retriever: str = "bm25") -> dict:
    qs = yaml.safe_load(Path(questions_path).read_text(encoding="utf-8"))
    db = sqlite3.connect(index_path)
    name, commit = db.execute("SELECT name, commit_sha FROM corpus").fetchone()
    db.close()
    pinned = str(qs["corpus"]["commit"])
    if not commit.startswith(pinned):
        raise ValueError(f"index is at {commit[:12]} but the evaluation set is pinned to {pinned}")

    from .embed import RRF_K, open_retriever

    index = open_retriever(index_path, retriever)
    items = []
    for it in qs["items"]:
        if it["type"] == "safety":
            continue
        gold = [(qs["files"][g["f"]], g["lines"][0], g["lines"][1]) for g in it["gold"]]
        hits = index.search(it["q"], k=max(KS))
        rank = next((r for r, h in enumerate(hits, 1) if any(overlaps(h, *g) for g in gold)), None)
        covered = sum(any(overlaps(h, *g) for h in hits) for g in gold)
        has_numbers = bool(_NUM.search(" ".join(it.get("must_include", []))))
        items.append({
            "id": it["id"],
            "type": it["type"],
            "first_gold_rank": rank,
            "evidence_rank": evidence_rank(hits, it.get("must_include", [])) if has_numbers else "n/a",
            "gold_ranges_covered_at_10": f"{covered}/{len(gold)}",
            "top": [f"{h.path}:{h.start_line}-{h.end_line}" for h in hits[:5]],
        })

    def summarize(subset: list[dict]) -> dict:
        n = len(subset)
        out = {"n": n}
        for k in KS:
            hit = sum(1 for i in subset if i["first_gold_rank"] and i["first_gold_rank"] <= k)
            out[f"recall@{k}"] = f"{hit}/{n} ({hit / n:.0%})" if n else "0/0"
        out["mrr@10"] = round(sum(1 / i["first_gold_rank"] for i in subset if i["first_gold_rank"]) / n, 3) if n else 0
        numeric = [i for i in subset if i["evidence_rank"] != "n/a"]
        for k in (5, 10):
            found = sum(1 for i in numeric if i["evidence_rank"] and i["evidence_rank"] <= k)
            out[f"evidence@{k}"] = f"{found}/{len(numeric)}" if numeric else "n/a"
        return out

    by_type = defaultdict(list)
    for i in items:
        by_type[i["type"]].append(i)
    return {
        "corpus": name,
        "commit": commit,
        "retriever": ("bm25 (k1=1.5, b=0.75)" if retriever == "bm25" else
                      f"hybrid: bm25 + {index.model} vectors, reciprocal rank fusion (k={RRF_K})"),
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall": summarize(items),
        "by_type": {t: summarize(v) for t, v in by_type.items()},
        "items": items,
    }


def write_results(results: dict, out_dir: str | Path, aggregate_only: bool = False) -> Path:
    """Write a run's results. With aggregate_only, per-item rows (which reveal questions' content) are left out."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = results["run_at"].replace(":", "").replace("-", "")[:15]
    tag = "" if results["retriever"].startswith("bm25") else "-hybrid"
    path = out_dir / f"retrieval-{results['corpus']}{tag}-{stamp}.json"
    payload = {k: v for k, v in results.items() if not (aggregate_only and k == "items")}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
