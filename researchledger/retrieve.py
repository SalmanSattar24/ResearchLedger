"""Keyword retrieval (BM25) over the chunks of one index.

This is the keyword half of the planned hybrid search; vector search (Vertex AI embeddings in BigQuery) is added
in the GCP step and fused with these scores. Each chunk is indexed with its file path and heading path, so
"8B" in a question can match the "Marin 8B Retrospective" heading even when the chunk body never says it.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_TOKEN = re.compile(r"[a-z0-9]+(?:[._\-][a-z0-9]+)*")
_STOPWORDS = frozenset(
    "a an and are as at be by did do does for from had has have how in is it its of on or that the their this to "
    "was were what when which who why with".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens; compounds such as 'qk-norm' or '1.7e-3' are kept whole and also split into parts."""
    tokens = []
    for t in _TOKEN.findall(text.lower()):
        if t not in _STOPWORDS:
            tokens.append(t)
        if any(sep in t for sep in "._-") and not re.fullmatch(r"[\d.]+", t):
            tokens += [p for p in re.split(r"[._\-]", t) if p and p not in _STOPWORDS]
    return tokens


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    path: str
    start_line: int
    end_line: int
    heading: str
    text: str
    score: float


class BM25Index:
    def __init__(self, index_path: str | Path, k1: float = 1.5, b: float = 0.75):
        db = sqlite3.connect(index_path)
        self.rows = db.execute("SELECT id, path, start_line, end_line, heading, text FROM chunks ORDER BY id").fetchall()
        db.close()
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(f"{path} {heading}\n{text}")) for _, path, _, _, heading, text in self.rows]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(len(self.lengths), 1)
        df: Counter[str] = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 10) -> list[Hit]:
        q = set(tokenize(query))
        scored = []
        for i, doc in enumerate(self.docs):
            s = 0.0
            norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg_len)
            for t in q:
                if tf := doc.get(t):
                    s += self.idf[t] * tf * (self.k1 + 1) / (tf + norm)
            if s > 0:
                scored.append((s, i))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [Hit(*self.rows[i][:6], score=s) for s, i in scored[:k]]
