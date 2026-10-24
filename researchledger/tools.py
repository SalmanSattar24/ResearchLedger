"""Read-only tools over one index, used by the agents and the verifier.

Every tool returns plain JSON-serialisable data. Nothing here can change the index: SQL runs on a read-only
connection with `PRAGMA query_only`, and only a single SELECT (or WITH ... SELECT) statement is accepted.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

from .retrieve import BM25Index  # noqa: F401 (re-exported for callers)

MAX_TEXT = 600  # characters of chunk text returned by search
MAX_TABLE_TEXT = 900  # the same for a chunk holding a table, whose rows are wide
MAX_LINES = 40  # lines returned by one read_lines call
MAX_ROWS = 200  # rows returned by one SQL query

_SELECT_ONLY = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b",
                        re.IGNORECASE)


_TABLE_SEP = re.compile(r"^\|[\s:|-]+\|?$")


def _compact(text: str) -> str:
    """A Markdown table row without its alignment padding ("|    63.2 |" -> "| 63.2 |"); other lines unchanged."""
    if not text.lstrip().startswith("|"):
        return text
    return "| " + " | ".join(c.strip() for c in text.strip().strip("|").split("|")) + " |"


def _fit(query: str, rows: list[tuple[int, str]], limit: int = MAX_TEXT) -> str:
    """Numbered lines of a chunk within `limit` characters. A long chunk keeps the lines that share the most terms
    with the query (in file order, gaps marked), not just its first lines. Table rows lose their padding and their
    separator row, and a kept row brings its table's header row, so a value is never shown without its column."""
    from .retrieve import tokenize

    rows = [(n, _compact(t)) for n, t in rows if not _TABLE_SEP.match(t.strip())]
    numbered = [f"{n}: {t}" for n, t in rows]
    if sum(len(x) + 1 for x in numbered) <= limit:
        return "\n".join(numbered)
    is_row = [t.lstrip().startswith("|") for _, t in rows]
    header = {}  # row index -> index of its table's header row (the first of a run of table rows)
    for i, r in enumerate(is_row):
        if r:
            header[i] = header[i - 1] if i and is_row[i - 1] else i
    q = set(tokenize(query))
    ranked = sorted(range(len(rows)), key=lambda i: (-len(q & set(tokenize(rows[i][1]))), i))
    keep, used = set(), 0
    for i in ranked:
        add = {i, header.get(i, i)} - keep
        cost = sum(len(numbered[j]) + 1 for j in add)
        if used + cost > limit and keep:
            continue
        keep |= add
        used += cost
    out, prev = [], -1
    for i in sorted(keep):
        if prev >= 0 and i != prev + 1:
            out.append("[...]")
        out.append(numbered[i] if len(numbered[i]) <= limit else numbered[i][:limit] + " [...]")
        prev = i
    if max(keep) < len(rows) - 1:
        out.append("[...]")
    return "\n".join(out)


class LedgerIndex:
    def __init__(self, index_path: str | Path, retriever: str | None = None, embed=None, sql_backend: str | None = None):
        from .embed import open_retriever

        self.path = Path(index_path)
        self.retriever = open_retriever(self.path, retriever, embed)
        self.db = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
        self.db.execute("PRAGMA query_only = ON")
        self.archived = {p for (p,) in self.db.execute("SELECT path FROM documents WHERE archived = 1")}
        self.name, self.commit = self.db.execute("SELECT name, commit_sha FROM corpus").fetchone()
        # SQL backend: 'sqlite' (this file) or 'bigquery' (the exported dataset; it must hold the same commit)
        self.sql_backend = sql_backend or os.environ.get("RL_SQL_BACKEND", "sqlite")
        self.sql = None
        if self.sql_backend == "bigquery":
            from .bigquery import BigQuerySQL

            self.sql = BigQuerySQL()
            got = self.sql.run_sql("SELECT commit_sha FROM corpus")
            if "error" in got or not got["rows"] or got["rows"][0][0] != self.commit:
                raise RuntimeError(f"BigQuery dataset does not hold commit {self.commit[:12]}: {got}")
        elif self.sql_backend != "sqlite":
            raise ValueError(f"unknown SQL backend: {self.sql_backend}")

    # ---------------------------------------------------------------- retrieval
    def search(self, query: str, k: int = 5) -> list[dict]:
        """Chunks whose non-blank lines are each prefixed with their line number, so citations can be exact."""
        out = []
        for h in self.retriever.search(query, k=max(1, min(k, 10))):
            rows = self.db.execute(
                "SELECT line, text FROM doc_lines WHERE path = ? AND line BETWEEN ? AND ? ORDER BY line",
                (h.path, h.start_line, h.end_line),
            ).fetchall()
            out.append({
                "path": h.path,
                "lines": f"{h.start_line}-{h.end_line}",
                "heading": h.heading,
                "archived": h.path in self.archived,
                "text": _fit(query, kept := [(n, t) for n, t in rows if t.strip()],
                             MAX_TABLE_TEXT if any(t.lstrip().startswith("|") for _, t in kept) else MAX_TEXT),
            })
        return out

    def read_lines(self, path: str, start: int, end: int) -> dict:
        start, end = int(start), int(end)
        if end < start:
            start, end = end, start
        end = min(end, start + MAX_LINES - 1)
        rows = self.db.execute(
            "SELECT line, text FROM doc_lines WHERE path = ? AND line BETWEEN ? AND ? ORDER BY line", (path, start, end)
        ).fetchall()
        if not rows:
            exists = self.db.execute("SELECT 1 FROM documents WHERE path = ?", (path,)).fetchone()
            return {"error": "no indexed lines in that range" if exists else f"not an indexed file: {path}"}
        return {"path": path, "archived": path in self.archived, "lines": [f"{n}: {t}" for n, t in rows]}

    def heading_at(self, path: str, line: int) -> str:
        """Section heading of the chunk containing a line ('' if none)."""
        row = self.db.execute(
            "SELECT heading FROM chunks WHERE path = ? AND start_line <= ? AND end_line >= ? LIMIT 1", (path, line, line)
        ).fetchone()
        if row is None:  # a blank line between chunks: use the nearest chunk above
            row = self.db.execute(
                "SELECT heading FROM chunks WHERE path = ? AND start_line <= ? ORDER BY start_line DESC LIMIT 1",
                (path, line)).fetchone()
        return row[0] if row else ""

    def line_texts(self, path: str, start: int, end: int) -> list[str]:
        """Exact indexed text of the lines in a range (for the verifier)."""
        return [t for (t,) in self.db.execute(
            "SELECT text FROM doc_lines WHERE path = ? AND line BETWEEN ? AND ? ORDER BY line", (path, start, end))]

    # ---------------------------------------------------------------- tables
    def list_tables(self, keyword: str = "") -> list[dict]:
        like = f"%{keyword.lower()}%"
        rows = self.db.execute(
            "SELECT t.id, t.path, t.start_line, t.end_line, t.heading, t.columns, "
            "(SELECT count(DISTINCT row_idx) FROM table_cells c WHERE c.table_id = t.id) "
            "FROM tables t WHERE lower(t.heading) LIKE ? OR lower(t.columns) LIKE ? OR lower(t.path) LIKE ? "
            "ORDER BY t.path, t.start_line LIMIT 40",
            (like, like, like),
        ).fetchall()
        return [
            {"table_id": i, "path": p, "lines": f"{a}-{b}", "heading": h, "columns": c, "rows": n,
             "archived": p in self.archived}
            for i, p, a, b, h, c, n in rows
        ]

    def run_sql(self, query: str) -> dict:
        q = query.strip().rstrip(";")
        if ";" in q or not _SELECT_ONLY.match(q) or _FORBIDDEN.search(q):
            return {"error": "only a single read-only SELECT statement is allowed"}
        if self.sql is not None:
            return self.sql.run_sql(q)
        try:
            cur = self.db.execute(q)
            rows = cur.fetchmany(MAX_ROWS + 1)
        except sqlite3.Error as e:
            return {"error": f"SQL error: {e}"}
        cols = [d[0] for d in cur.description or []]
        return {"columns": cols, "rows": [list(r) for r in rows[:MAX_ROWS]], "truncated": len(rows) > MAX_ROWS}
