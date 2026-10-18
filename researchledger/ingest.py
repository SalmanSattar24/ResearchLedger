"""Ingestion: corpus at a pinned commit -> leakage-checked chunks and tables in a SQLite index.

The index is built in a temporary file and moved into place only if every file passed the leakage scan, so a
refused corpus never leaves a partial index behind.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .chunking import chunk_document
from .corpus import CorpusConfig, GitSource
from .documents import UnsupportedDocument, document_lines
from .leakage import ALLOWED_EXTENSIONS, EMBEDDED_IMAGE, Finding, LeakageError, Redaction, is_allowed, scan_lines
from .tables import extract_tables, to_number

SCHEMA = """
CREATE TABLE corpus (name TEXT, source TEXT, commit_sha TEXT, ingested_at TEXT, report TEXT);
CREATE TABLE chunks (id INTEGER PRIMARY KEY, path TEXT, start_line INTEGER, end_line INTEGER, heading TEXT, text TEXT,
                     line_numbers TEXT);
CREATE TABLE tables (id INTEGER PRIMARY KEY, path TEXT, start_line INTEGER, end_line INTEGER, heading TEXT,
                     columns TEXT);
CREATE TABLE table_cells (table_id INTEGER, row_idx INTEGER, line INTEGER, col_idx INTEGER, col_name TEXT,
                          text TEXT, num REAL);
CREATE TABLE redactions (path TEXT, line INTEGER, param TEXT);
"""


def _ext(path: str) -> str:
    return PurePosixPath(path).suffix.lower() or "(none)"


def ingest(config: CorpusConfig, out_path: str | Path, source: GitSource | None = None) -> dict:
    source = source or GitSource(config)
    files = source.list_files()

    findings: list[Finding] = []
    redactions: list[Redaction] = []
    ingested: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    unsupported: list[dict] = []
    chunks, tables = [], []

    for path in files:
        if not is_allowed(path):
            skipped[_ext(path)] += 1
            continue
        try:
            lines = document_lines(path, source.read(path))
        except UnsupportedDocument as e:
            unsupported.append({"path": path, "reason": str(e)})
            continue
        scan = scan_lines(path, lines)
        findings += scan.findings
        redactions += scan.redactions
        ingested[_ext(path)] += 1
        chunks += chunk_document(path, scan.lines)
        tables += extract_tables(path, scan.lines)

    if findings:
        raise LeakageError(findings)

    report = {
        "corpus": config.name,
        "commit": source.commit,
        "files_listed": len(files),
        "files_ingested": dict(sorted(ingested.items())),
        "files_skipped_by_extension": dict(sorted(skipped.items())),
        "files_unsupported": unsupported,
        "chunks": len(chunks),
        "tables": len(tables),
        "redactions": len(redactions),
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".building")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    with db:
        db.executescript(SCHEMA)
        db.execute(
            "INSERT INTO corpus VALUES (?, ?, ?, ?, ?)",
            (config.name, config.source, source.commit, datetime.now(timezone.utc).isoformat(), json.dumps(report)),
        )
        db.executemany(
            "INSERT INTO chunks (path, start_line, end_line, heading, text, line_numbers) VALUES (?, ?, ?, ?, ?, ?)",
            [(c.path, c.start_line, c.end_line, c.heading, c.text, json.dumps(c.line_numbers)) for c in chunks],
        )
        for t in tables:
            cur = db.execute(
                "INSERT INTO tables (path, start_line, end_line, heading, columns) VALUES (?, ?, ?, ?, ?)",
                (t.path, t.start_line, t.end_line, t.heading, json.dumps(t.columns)),
            )
            db.executemany(
                "INSERT INTO table_cells VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (cur.lastrowid, r, line, c, t.columns[c] if c < len(t.columns) else "", cell, to_number(cell))
                    for r, (line, cells) in enumerate(t.rows)
                    for c, cell in enumerate(cells)
                ],
            )
        db.executemany("INSERT INTO redactions VALUES (?, ?, ?)", [(r.path, r.line, r.param) for r in redactions])
    db.close()
    verify_index(tmp)
    os.replace(tmp, out_path)
    return report


def verify_index(index_path: str | Path) -> None:
    """Leakage gate on a built index: only allowed document types, no embedded images, no unredacted URL tokens."""
    db = sqlite3.connect(index_path)
    try:
        bad = []
        for path, start, text in db.execute("SELECT path, start_line, text FROM chunks"):
            if not path.lower().endswith(ALLOWED_EXTENSIONS):
                bad.append(f"{path}: file type not allowed")
            if EMBEDDED_IMAGE.search(text):
                bad.append(f"{path}:{start}: embedded image")
        if bad:
            raise AssertionError("leakage gate failed:\n" + "\n".join(bad))
    finally:
        db.close()
