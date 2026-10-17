# ResearchLedger

An evidence-checked assistant for research repositories. It answers questions over a project's record (research
log, deviations log, protocol, notebooks, result tables) with citations to the exact file, line and commit, keeps
track of facts that were later superseded, and checks whether a claim (in a CV, abstract or draft) is backed by the
record.

Status: **design and evaluation method (17 Oct 2026); no code yet.** Each corpus's evaluation set and the pass
thresholds (`eval/THRESHOLDS.md`) are fixed before anything is built.

## Design

```
Git repo (pinned commit)
  └─ ingestion job ── allowlist (git ls-files, text only) + leakage scan (refuses person identifiers, data files)
       ├─ unstructured: Markdown/LaTeX sections, notebook Markdown + printed outputs → chunks
       │    (file, line range, date, commit, section) → Vertex AI embeddings
       └─ structured: deviations log rows, result CSVs → typed tables (date, section, change, results seen?)
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
ResearchLedger does not restate), notebook outputs, or credentials. Ingestion fails if an image or data file, or a token
pattern, is found.

## Plan

1. Evaluation sets and thresholds, approved before code: private corpus (approved 17 Oct 2026), then the public
   demo corpus (Marin).
2. Local ingestion and retrieval, measured against both evaluation sets.
3. Verifier and agents (ADK, Gemini).
4. GCP: BigQuery, Cloud Run, Terraform, CI, MCP endpoint, tracing.
5. Evaluation report with every result, including failures (per item for the demo corpus, in aggregate for the
   private corpus); field notes on friction in the stack (`docs/FIELD_NOTES.md`).
