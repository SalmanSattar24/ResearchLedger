"""Vector half of hybrid retrieval: Vertex AI embeddings for every chunk, fused with BM25 by reciprocal rank.

`embed_index` adds a `chunk_vectors` table to a built index (one float32 vector per chunk, with the model that made
it). `HybridIndex` ranks chunks by BM25 and by cosine similarity to the question's embedding, and fuses the two
rankings with reciprocal rank fusion (RRF), which needs no score calibration between them. The embedded text is
the same text BM25 indexes: file path, heading path and chunk body.

Embedding sends chunk text to Vertex AI, so it is run only for corpora cleared for that (the public demo corpus).
"""

from __future__ import annotations

import math
import os
import sqlite3
from array import array
from pathlib import Path
from typing import Callable

from .retrieve import BM25Index, Hit

EMBED_MODEL = os.environ.get("RL_EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 768
RRF_K = 60  # the usual RRF constant; larger flattens the contribution of top ranks
POOL = 50  # candidates taken from each ranking before fusion
BATCH = 50

Embedder = Callable[[list[str], str], list[list[float]]]  # (texts, task_type) -> vectors


def vertex_embedder(model: str = EMBED_MODEL, dim: int = EMBED_DIM) -> Embedder:
    from google.genai import types

    from .llm import genai_client

    client = genai_client()

    def embed(texts: list[str], task: str) -> list[list[float]]:
        out = []
        for i in range(0, len(texts), BATCH):
            resp = client.models.embed_content(
                model=model, contents=texts[i:i + BATCH],
                config=types.EmbedContentConfig(task_type=task, output_dimensionality=dim))
            out += [e.values for e in resp.embeddings]
        return out

    return embed


def _unit(v: list[float]) -> array:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return array("f", (x / n for x in v))


def chunk_texts(db: sqlite3.Connection) -> list[tuple[int, str]]:
    return [(i, f"{path} {heading}\n{text}")
            for i, path, heading, text in db.execute("SELECT id, path, heading, text FROM chunks ORDER BY id")]


def embed_index(index_path: str | Path, embed: Embedder | None = None, model: str = EMBED_MODEL) -> dict:
    """Embed every chunk of an index in place. Re-running replaces the vectors."""
    embed = embed or vertex_embedder(model)
    db = sqlite3.connect(index_path)
    rows = chunk_texts(db)
    vectors = embed([t for _, t in rows], "RETRIEVAL_DOCUMENT")
    db.execute("DROP TABLE IF EXISTS chunk_vectors")
    db.execute("CREATE TABLE chunk_vectors (chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id), model TEXT, "
               "dim INTEGER, vector BLOB)")
    db.executemany("INSERT INTO chunk_vectors VALUES (?, ?, ?, ?)",
                   [(i, model, len(v), _unit(v).tobytes()) for (i, _), v in zip(rows, vectors)])
    db.commit()
    db.close()
    return {"chunks": len(rows), "model": model, "dim": len(vectors[0]) if vectors else 0}


def has_vectors(index_path: str | Path) -> bool:
    db = sqlite3.connect(index_path)
    try:
        return db.execute("SELECT count(*) FROM sqlite_master WHERE name = 'chunk_vectors'").fetchone()[0] == 1
    finally:
        db.close()


def open_retriever(index_path: str | Path, kind: str | None = None, embed: Embedder | None = None):
    """'bm25', 'hybrid', or 'auto' (hybrid when the index has vectors). Default: RL_RETRIEVER, else 'auto'."""
    kind = kind or os.environ.get("RL_RETRIEVER", "auto")
    if kind == "hybrid" or (kind == "auto" and has_vectors(index_path)):
        return HybridIndex(index_path, embed)
    if kind in ("bm25", "auto"):
        return BM25Index(index_path)
    raise ValueError(f"unknown retriever: {kind}")


class HybridIndex:
    """BM25 and vector rankings fused by RRF. Same interface as BM25Index.search; Hit.score is the fused score."""

    def __init__(self, index_path: str | Path, embed: Embedder | None = None):
        self.bm25 = BM25Index(index_path)
        db = sqlite3.connect(index_path)
        self.model = db.execute("SELECT model FROM chunk_vectors LIMIT 1").fetchone()[0]
        self.vectors: dict[int, array] = {}
        for i, blob in db.execute("SELECT chunk_id, vector FROM chunk_vectors"):
            a = array("f")
            a.frombytes(blob)
            self.vectors[i] = a
        db.close()
        self.by_id = {r[0]: r for r in self.bm25.rows}
        self._embed = embed
        self.rankings: dict[str, list[int]] = {}  # last query's per-method ranking (for diagnostics)

    @property
    def embed(self) -> Embedder:
        if self._embed is None:
            self._embed = vertex_embedder(self.model)
        return self._embed

    def vector_ranking(self, query: str, n: int = POOL) -> list[int]:
        q = _unit(self.embed([query], "RETRIEVAL_QUERY")[0])
        scored = sorted(((sum(a * b for a, b in zip(q, v)), i) for i, v in self.vectors.items()),
                        key=lambda x: (-x[0], x[1]))
        return [i for _, i in scored[:n]]

    def search(self, query: str, k: int = 10) -> list[Hit]:
        lexical = [h.chunk_id for h in self.bm25.search(query, k=POOL)]
        semantic = self.vector_ranking(query)
        self.rankings = {"bm25": lexical, "vector": semantic}
        fused: dict[int, float] = {}
        for ranking in (lexical, semantic):
            for rank, i in enumerate(ranking, 1):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank)
        top = sorted(fused.items(), key=lambda x: (-x[1], x[0]))[:k]
        return [Hit(*self.by_id[i][:6], score=s) for i, s in top]
