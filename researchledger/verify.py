"""The answer format, and the verifier that every answer must pass before it is returned.

Two stages (README, "Design"):
1. Deterministic: every claim has at least one citation; each cited file and line range exists in the index; every
   number and every quoted phrase in a claim appears in the claim's cited lines (or in the cited file's path and
   section heading, so "8B" in "the 8B run" is satisfied by marin-8b-retro.md); a claim computed from a table
   carries its SQL, which is re-run here and must produce the claim's numbers; every number in the answer's prose
   appears in one of its claims. No model is involved, so these checks cannot be talked around.
2. Model check: for claims that pass stage 1, a model reads only the cited lines, with their file and section,
   and says whether they support the claim.
Failures go back to the coordinator once; if the retry still fails, the system abstains.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from .leakage import scan_lines
from .tools import LedgerIndex

_NUM = re.compile(r"(?<![\w.])[+-]?\d+(?:[.,]\d+)*(?:e-?\d+)?%?")
_QUOTE = re.compile("[\"“]([^\"”]{3,})[\"”]")
_DASHES = dict.fromkeys(map(ord, "‑‐–—−"), "-")


class Citation(BaseModel):
    path: str
    start: int
    end: int


class Claim(BaseModel):
    text: str
    citations: list[Citation] = Field(default_factory=list)
    sql: str | None = None  # for a value computed from a table: the read-only query that computes it


class Answer(BaseModel):
    status: Literal["answered", "refused", "abstained"]
    answer: str = ""
    claims: list[Claim] = Field(default_factory=list)
    verdict: Literal["supported", "partly", "unsupported"] | None = None
    reason: str = ""

    @field_validator("answer", "reason", mode="before")
    @classmethod
    def _none_is_empty(cls, v):
        return "" if v is None else v

    @field_validator("claims", mode="before")
    @classmethod
    def _none_is_no_claims(cls, v):
        return [] if v is None else v


def parse_answer(text: str) -> Answer:
    """Parse the coordinator's final JSON (tolerating a Markdown code fence around it)."""
    body = text.strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", body)
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in the answer")
    try:
        return Answer.model_validate(json.loads(body[start:end + 1]))
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"answer is not valid JSON for the schema: {e}") from e


def _norm(s: str) -> str:
    return s.translate(_DASHES).replace("≈", "").replace("**", "").lower()


def numbers(text: str) -> set[str]:
    """Numbers as written, normalised: '1,159' -> '1159', '92.6%' -> '92.6'."""
    return {n.replace(",", "").rstrip("%").lstrip("+") for n in _NUM.findall(_norm(text))}


def _has_number(n: str, text: str) -> bool:
    t = _norm(text).replace(",", "")
    return re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", t) is not None


def citation_context(index: LedgerIndex, cit: Citation) -> str:
    """The cited file's path and the section heading of the cited lines."""
    return f"{cit.path} [{index.heading_at(cit.path, cit.start)}]"


def check_deterministic(answer: Answer, index: LedgerIndex) -> list[str]:
    problems: list[str] = []
    text = answer.answer + "\n" + "\n".join(c.text for c in answer.claims)
    for f in scan_lines("answer", list(enumerate(text.split("\n"), 1))).findings:
        problems.append(f"answer contains a {f.kind}")
    if answer.status != "answered":
        if answer.claims:
            problems.append("a refusal or abstention must not carry claims")
        return problems
    if not answer.claims:
        problems.append("an answer must have at least one cited claim")
    supported_numbers: set[str] = set()
    context_text = ""
    for i, c in enumerate(answer.claims, 1):
        if not c.citations:
            problems.append(f"claim {i} has no citation: {c.text!r}")
            continue
        cited = []
        for cit in c.citations:
            texts = index.line_texts(cit.path, cit.start, cit.end)
            if not texts:
                problems.append(f"claim {i} cites {cit.path}:{cit.start}-{cit.end}, which has no indexed lines")
            cited += texts
            context_text += citation_context(index, cit) + "\n"
        joined = "\n".join(cited)
        if cited and not joined.strip():
            problems.append(f"claim {i} cites only blank lines")
        evidence = joined + "\n" + "\n".join(citation_context(index, cit) for cit in c.citations)
        if c.sql:
            res = index.run_sql(c.sql)
            if "error" in res:
                problems.append(f"claim {i}: its SQL failed to run: {res['error']}")
            else:  # the query's own constants (e.g. a threshold), its rows and its row count all count
                evidence += "\n" + sql_evidence(c.sql, res)
        for n in sorted(numbers(c.text)):
            supported_numbers.add(n)
            if joined and not _has_number(n, evidence):
                where = "its cited lines or its SQL result" if c.sql else "its cited lines"
                problems.append(f"claim {i}: the number {n} is not in {where}")
        for q in _QUOTE.findall(c.text):
            if joined and _norm(q) not in _norm(joined):
                problems.append(f"claim {i}: the quoted text {q!r} is not in its cited lines")
    for n in sorted(numbers(answer.answer) - supported_numbers):
        if not _has_number(n, context_text):
            problems.append(f"the answer states {n}, which no cited claim contains")
    if problems:
        problems.append("what the cited lines actually say:\n" + cited_text(answer, index))
    return problems


def sql_evidence(query: str, result: dict) -> str:
    """What a computed claim may draw numbers from: the query text, its rows, and how many rows it returned."""
    return f"{query}\n{json.dumps(result['rows'])}\nrows returned: {len(result['rows'])}"


def attach_sql(answer: Answer, index: LedgerIndex, queries: list[str]) -> list[str]:
    """Give a computed claim that came back without its query the query sql_agent actually ran.

    A claim with no `sql` whose numbers are missing from its cited lines gets the first query run in this attempt
    whose text and result contain all of them. The query is re-run here, and again by check_deterministic, so
    nothing is taken on trust. Returns a note per attached query (for the trace)."""
    notes = []
    for i, c in enumerate(answer.claims, 1):
        if c.sql or not c.citations:
            continue
        cited = "\n".join(t for cit in c.citations for t in index.line_texts(cit.path, cit.start, cit.end))
        cited += "\n" + "\n".join(citation_context(index, cit) for cit in c.citations)
        missing = [n for n in numbers(c.text) if not _has_number(n, cited)]
        if not missing:
            continue
        for q in queries:
            res = index.run_sql(q)
            if "error" not in res and all(_has_number(n, sql_evidence(q, res)) for n in missing):
                c.sql = q
                notes.append(f"claim {i}: attached the query sql_agent ran: {q}")
                break
    return notes


def cited_text(answer: Answer, index: LedgerIndex, max_chars: int = 300) -> str:
    """Each claim's cited lines, so a retry can see what its citations really say."""
    out = []
    for i, c in enumerate(answer.claims, 1):
        for cit in c.citations:
            text = " | ".join(index.line_texts(cit.path, cit.start, cit.end)).strip() or "(no text)"
            out.append(f"  claim {i}, {cit.path}:{cit.start}-{cit.end}: {text[:max_chars]}")
    return "\n".join(out)


def claim_evidence(claim: Claim, index: LedgerIndex) -> str:
    """Cited lines with their file and section (and the SQL result for a computed claim), for a model check."""
    blocks = []
    for cit in claim.citations:
        rows = index.read_lines(cit.path, cit.start, cit.end).get("lines", [])
        blocks.append(f"File {citation_context(index, cit)}:\n" + "\n".join(rows))
    if claim.sql:
        res = index.run_sql(claim.sql)
        blocks.append("Computed by SQL over the parsed table (query, result rows, row count):\n" +
                      (sql_evidence(claim.sql, res) if "error" not in res else f"{claim.sql}\n{res['error']}"))
    return "\n".join(blocks)


SUPPORT_PROMPT = """You check citations. For each claim, read ONLY the cited lines given with it (and, for a
computed claim, the SQL result over those table rows) and decide whether they state or directly imply the claim.
The file name and section heading are part of the context. Do not use outside knowledge. A claim that adds
anything the evidence does not say is not supported. Ignore wording about where or by whom something is said (for
example "the record states", "the summary says"); judge only the factual content.

Return JSON only: {"results": [{"claim": <number>, "supported": true|false, "why": "<one short sentence>"}]}

Claims:
"""


def check_support(answer: Answer, index: LedgerIndex, client, model: str, usage=None) -> list[str]:
    """Model check of claims against their cited lines. Returns problems for unsupported claims."""
    if answer.status != "answered" or not answer.claims:
        return []
    parts = [f"[{i}] {c.text}\n{claim_evidence(c, index)}" for i, c in enumerate(answer.claims, 1)]
    from google.genai import types

    from .llm import CALL_TIMEOUT_MS, RETRY

    if usage is not None:
        usage.start("verifier")
    resp = client.models.generate_content(
        model=model,
        contents=SUPPORT_PROMPT + "\n\n".join(parts),
        config=types.GenerateContentConfig(
            temperature=0, response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_level="low"),
            http_options=types.HttpOptions(timeout=CALL_TIMEOUT_MS["verifier"], retry_options=RETRY)),
    )
    if usage is not None:
        usage.record("verifier", model, resp.usage_metadata)
    try:
        results = json.loads(resp.text)["results"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return ["the citation check returned no usable result"]
    problems = [f"claim {r.get('claim')} is not supported by its cited lines: {r.get('why', '')}"
                for r in results if not r.get("supported")]
    if problems:
        problems.append("what the cited lines actually say:\n" + cited_text(answer, index))
    return problems
