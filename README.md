# ResearchLedger

An evidence-checked assistant for research repositories. It answers questions over a project's record (research
log, deviations log, protocol, notebooks, result tables) with citations to the exact file, line and commit, keeps
track of facts that were later superseded, and checks whether a claim (in a CV, abstract or draft) is backed by the
record.

Status (17 Oct 2026): **step 2, local ingestion and keyword retrieval, is built and measured; no agents yet.**
Each corpus's evaluation set and the pass thresholds (`eval/THRESHOLDS.md`) were fixed before any code was written.
Retrieval results so far: [`eval/results/`](eval/results/README.md).

## Design

```
Git repo (pinned commit)
  └─ ingestion job ── allowlist (git ls-files, text only) + leakage scan (refuses data files, secrets, private person identifiers;
                                                                   redacts URL tokens)
       ├─ unstructured: Markdown/LaTeX sections, notebook Markdown cells (never outputs) → chunks
       │    (file, line range, date, commit, section) → Vertex AI embeddings
       └─ structured: Markdown tables (e.g. deviations log, result tables) → typed cells (row, column, number)
                         ▼
                  BigQuery (chunks + embeddings, tables; VECTOR_SEARCH + keyword search)
                         ▼
  ADK agents on Cloud Run
    coordinator (hierarchical delegation)
      ├─ retrieval agent (ReAct: hybrid search, reads neighbouring lines, follows "superseded by" links)
      ├─ SQL agent (ReAct: read-only queries over the tables)
      └─ verifier (self-reflection): every number/quote must appear in the cited lines (deterministic),
         then an LLM check that the lines support the claim; failures go back for one retry, else abstain
                         ▼
  REST API · MCP server (used by Claude Code in research sessions) · tracing (OpenTelemetry → Cloud Trace)
  metrics per request: latency per step, tokens in/out, tokens/sec, cost; session state persisted
```

Production: Terraform for all infrastructure; CI runs unit tests and the public evaluation set and blocks a deploy
that misses a gate; Cloud Run with IAM-only access; Secret Manager; staging and production services.

## Data boundary

Two corpora:

- **Private research corpus:** an unpublished research project's record. Its evaluation set (41 items), index and
  per-item results stay in a private repository and are run outside this repository's CI. Only aggregate scores are
  published here.
- **Public demo corpus:** [Marin](https://github.com/marin-community/marin) (open lab for foundation models;
  Apache-2.0, as read from its `LICENSE` file), pinned at commit 5e12684. Only its human-written reports and
  experiment logs (`docs/reports/`, `docs/experiments/`) are used; the agent-written `.agents/` folder is not. It has a
  public evaluation set, so anyone can run the tool and check each answer against the cited lines. Contributor names
  in it are public and allowed through the leakage scan, but no question asks about a person.

Only text is ingested: Markdown, LaTeX and notebook Markdown from the repository's tracked files. Never ingested:
images, dataset manifests or label files (the public datasets keep their own licences, which
ResearchLedger does not restate), notebook outputs, or credentials.

Leakage scan:

- **Fails** ingestion on an image or data file, or on anything that looks like a real secret (API keys, private
  keys, cloud credentials, `.env`-style assignments).
- **Redacts** tokens in URL query parameters (e.g. `accessToken=`, `token=`, `key=`), such as share links to experiment
  dashboards, which public research documents sometimes contain. Each value is replaced with `[REDACTED]`, and each
  redaction is logged (file, line, parameter name; never the value). The log is kept with the index, and the
  redacted value is never produced in an answer.

## Running locally (step 2)

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m researchledger ingest --corpus corpora/marin.yaml --index .cache/index/marin.sqlite
python -m researchledger search --index .cache/index/marin.sqlite "Why did the 32B run switch to QK-Norm?"
python -m researchledger eval-retrieval --index .cache/index/marin.sqlite --questions eval/questions.yaml --out eval/results
```

Ingestion reads the pinned commit from git objects (a blobless clone into `.cache/` for a remote corpus), so the
source working tree is never read or changed. The index is SQLite locally; BigQuery replaces it in step 4.

## Plan

1. Evaluation sets and thresholds, approved before code: private corpus (approved 17 Oct 2026), then the public
   demo corpus (Marin).
2. Local ingestion and retrieval, measured against both evaluation sets.
3. Verifier and agents (ADK, Gemini).
4. GCP: BigQuery, Cloud Run, Terraform, CI, MCP endpoint, tracing.
5. Evaluation report with every result, including failures (per item for the demo corpus, in aggregate for the
   private corpus); field notes on friction in the stack (`docs/FIELD_NOTES.md`).
