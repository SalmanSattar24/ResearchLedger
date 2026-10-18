"""BigQuery: the cloud copy of an index, the SQL agent's table store, and vector search over chunks.

`export_index` loads every table of a built SQLite index (and its chunk vectors, if embedded) into one BigQuery
dataset, replacing what was there, and records the corpus commit. The SQLite file and the dataset are written
from the same ingestion run, so they hold the same rows; `verify_export` checks the row counts match.

`BigQuerySQL` runs the SQL agent's queries in BigQuery. Read-only is enforced twice: the service account that
runs the service has only data-viewer access to the dataset (Terraform, infra/), and every query is dry-run first
and refused unless BigQuery itself classifies it as a single SELECT. Bytes billed are capped per query.

`vector_search` ranks chunks by cosine distance to a query vector with VECTOR_SEARCH (brute force at this size; a
vector index needs 5,000+ rows).
"""

from __future__ import annotations

import json
import os
import sqlite3
from array import array
from pathlib import Path

from .llm import PROJECT

DATASET = os.environ.get("RL_BQ_DATASET", "researchledger_marin")
LOCATION = os.environ.get("RL_BQ_LOCATION", "US")
MAX_BYTES_BILLED = 100 * 1024 * 1024  # per query; the whole Marin dataset is under 2 MB
MAX_ROWS = 200

# BigQuery column types for each index table (same names and order as ingest.SCHEMA).
TABLES = {
    "corpus": [("name", "STRING"), ("source", "STRING"), ("commit_sha", "STRING"), ("ingested_at", "STRING"),
               ("report", "STRING")],
    "chunks": [("id", "INT64"), ("path", "STRING"), ("start_line", "INT64"), ("end_line", "INT64"),
               ("heading", "STRING"), ("text", "STRING"), ("line_numbers", "STRING")],
    "tables": [("id", "INT64"), ("path", "STRING"), ("start_line", "INT64"), ("end_line", "INT64"),
               ("heading", "STRING"), ("columns", "STRING")],
    "table_cells": [("table_id", "INT64"), ("row_idx", "INT64"), ("line", "INT64"), ("col_idx", "INT64"),
                    ("col_name", "STRING"), ("text", "STRING"), ("num", "FLOAT64")],
    "redactions": [("path", "STRING"), ("line", "INT64"), ("param", "STRING")],
    "doc_lines": [("path", "STRING"), ("line", "INT64"), ("text", "STRING")],
    "documents": [("path", "STRING"), ("archived", "INT64")],
}
VECTORS = [("chunk_id", "INT64"), ("model", "STRING"), ("embedding", "FLOAT64", "REPEATED")]


def client(project: str = PROJECT):
    import google.auth
    from google.cloud import bigquery

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"], quota_project_id=project)
    return bigquery.Client(project=project, credentials=creds, location=LOCATION,
                           default_job_creation_mode="JOB_CREATION_OPTIONAL")


def _schema(cols):
    from google.cloud import bigquery

    return [bigquery.SchemaField(c[0], c[1], mode=c[2] if len(c) > 2 else "NULLABLE") for c in cols]


def index_rows(index_path: str | Path) -> dict[str, list[dict]]:
    """Every row of every index table as JSON-ready dicts (vectors as float lists)."""
    db = sqlite3.connect(index_path)
    out = {}
    for table, cols in TABLES.items():
        names = [c[0] for c in cols]
        out[table] = [dict(zip(names, r)) for r in db.execute(f"SELECT {', '.join(names)} FROM {table}")]
    if db.execute("SELECT count(*) FROM sqlite_master WHERE name = 'chunk_vectors'").fetchone()[0]:
        out["chunk_vectors"] = []
        for i, model, blob in db.execute("SELECT chunk_id, model, vector FROM chunk_vectors"):
            a = array("f")
            a.frombytes(blob)
            out["chunk_vectors"].append({"chunk_id": i, "model": model, "embedding": [float(x) for x in a]})
    db.close()
    return out


def export_index(index_path: str | Path, dataset: str = DATASET, bq=None) -> dict:
    """Replace the dataset's tables with the index's rows. The dataset itself is created by Terraform."""
    from google.cloud import bigquery

    bq = bq or client()
    counts = {}
    for table, rows in index_rows(index_path).items():
        cols = VECTORS if table == "chunk_vectors" else TABLES[table]
        job = bq.load_table_from_json(
            rows, f"{bq.project}.{dataset}.{table}",
            job_config=bigquery.LoadJobConfig(schema=_schema(cols), write_disposition="WRITE_TRUNCATE"))
        job.result()
        counts[table] = len(rows)
    verify_export(counts, dataset, bq)
    return counts


def verify_export(expected: dict[str, int], dataset: str = DATASET, bq=None) -> None:
    bq = bq or client()
    for table, n in expected.items():
        got = list(bq.query_and_wait(f"SELECT count(*) AS n FROM `{bq.project}.{dataset}.{table}`"))[0]["n"]
        if got != n:
            raise RuntimeError(f"{dataset}.{table} has {got} rows, the index has {n}")


class BigQuerySQL:
    """The SQL tool over BigQuery: same contract as LedgerIndex.run_sql (columns, rows, truncated, or error)."""

    def __init__(self, dataset: str = DATASET, bq=None):
        from google.cloud import bigquery

        self.bq = bq or client()
        self.dataset = dataset
        self._bigquery = bigquery

    def _config(self, dry_run: bool):
        return self._bigquery.QueryJobConfig(
            default_dataset=f"{self.bq.project}.{self.dataset}", dry_run=dry_run, use_query_cache=not dry_run,
            maximum_bytes_billed=MAX_BYTES_BILLED)

    def run_sql(self, query: str) -> dict:
        from google.api_core import exceptions

        q = query.strip().rstrip(";")
        try:
            dry = self.bq.query(q, job_config=self._config(dry_run=True))
            if dry.statement_type != "SELECT":
                return {"error": "only a single read-only SELECT statement is allowed"}
            rows = self.bq.query_and_wait(q, job_config=self._config(dry_run=False), max_results=MAX_ROWS + 1)
            cols = [f.name for f in rows.schema]
            data = [list(r.values()) for r in rows]
        except exceptions.GoogleAPICallError as e:
            return {"error": f"SQL error: {getattr(e, 'message', str(e))[:300]}"}
        return {"columns": cols, "rows": data[:MAX_ROWS], "truncated": len(data) > MAX_ROWS}


def vector_search(query_vector: list[float], k: int = 10, dataset: str = DATASET, bq=None) -> list[dict]:
    """Top-k chunks by cosine distance, computed in BigQuery."""
    from google.cloud import bigquery

    bq = bq or client()
    sql = f"""
    SELECT base.chunk_id AS chunk_id, c.path, c.start_line, c.end_line, c.heading, distance
    FROM VECTOR_SEARCH(TABLE `{bq.project}.{dataset}.chunk_vectors`, 'embedding',
                       (SELECT @q AS embedding), top_k => @k, distance_type => 'COSINE')
    JOIN `{bq.project}.{dataset}.chunks` c ON c.id = base.chunk_id
    ORDER BY distance"""
    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter("q", "FLOAT64", query_vector),
                                                    bigquery.ScalarQueryParameter("k", "INT64", k)],
                                  maximum_bytes_billed=MAX_BYTES_BILLED)
    return [dict(r) for r in bq.query_and_wait(sql, job_config=cfg)]


def describe() -> str:
    return json.dumps({"project": PROJECT, "dataset": DATASET, "location": LOCATION})
