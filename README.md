# ResearchLedger

An evidence-checked assistant for research repositories. It answers questions over a project's record (research
log, deviations log, protocol, notebooks, result tables) with citations to the exact file, line and commit, keeps
track of facts that were later superseded, and checks whether a claim (in a CV, abstract or draft) is backed by the
record.

Status (18 Oct 2026): **step 3, the ADK agents and the verifier, is built and measured on the public set.**
- **Passing (8 of 12 graded gates):** citation support 99%, citation recall 95%, safety, cost ($0.010 per
  question), superseded handling and claim verdicts.
- **Failing:** answer accuracy (24/38; answers tend to leave out secondary facts) and latency (p95 52 s locally).
- Each corpus's evaluation set and the pass thresholds (`eval/THRESHOLDS.md`) were fixed before any code was
  written. All results, including failures, are in [`eval/results/`](eval/results/README.md).

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

Production: Terraform for all infrastructure; CI runs the unit tests, and the deploy workflow runs the public
evaluation set against staging and blocks promotion to production if a gate fails; Cloud Run with IAM-only access;
keyless credentials (Workload Identity Federation), so no stored secrets; staging and production services.

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

## Answering (step 3)

```bash
python -m pip install -e ".[dev,agents]"
gcloud auth application-default login   # once; the agents call Gemini on Vertex AI with these credentials
python -m researchledger ask --index .cache/index/marin.sqlite "Why did the 32B run switch to the Qwen3 backbone?"
python -m researchledger eval-answers --index .cache/index/marin.sqlite --questions eval/questions.yaml --out eval/results
```

How a question is answered (`researchledger/agents.py`):

1. **Retrieve first, then read.** A keyword search runs before any model call. Its top passages, each line with its
   number and an archived flag, go to the coordinator in its first message.
2. **Coordinator (ADK `LlmAgent`).** It answers from that evidence when it can (the fast path). When it can't, it
   delegates through `AgentTool` to:
   - a **retrieval agent**, which searches with new phrasings and reads exact lines, preferring current over
     archived files;
   - a **SQL agent**, which runs read-only queries over the parsed tables.
3. **Verifier (`researchledger/verify.py`).**
   - Deterministic checks first: each cited range exists; every number and quote in a claim is in its cited lines
     (or the file's path and section heading); a computed claim's SQL is re-run; no leakage in the answer.
   - Then a model reads only the cited lines and says whether they support each claim.
   - On failure the coordinator gets the reasons and the actual cited text for one retry. If that also fails, the
     system abstains.
4. **Accounting.** Every model call is timed and costed per agent.

Models run on Vertex AI in the project `researchledger-2026` (`RL_GCP_PROJECT`). The agents use
`gemini-3.7-flash`. (`gemini-3.8-flash` costs the same but answered a one-word prompt in a median 22.8 s on
18 Oct 2026, against 1.7 s for 3.7.) The judge in `eval-answers` is `gemini-2.5-pro`, a different model family from the agents, so
no model grades its own output. The quota project is set per process, so application-default credentials that
point at another project are not changed.

## On GCP (step 4, written; not yet applied)

```bash
python -m researchledger embed --index .cache/index/marin.sqlite            # Vertex AI embeddings, for hybrid search
python -m researchledger export-bigquery --index .cache/index/marin.sqlite  # load the index into BigQuery
uvicorn researchledger.service:app --port 8080                              # REST API + MCP endpoint, locally
```

- **Hybrid retrieval.** Each chunk gets a `gemini-embedding-001` vector (768 dimensions). Search fuses the BM25
  ranking and the vector ranking by reciprocal rank fusion. On Marin: recall@3 33 → 36 of 38, recall@10 37 → 38,
  MRR 0.84 → 0.87, evidence@5 29 → 27 of 32 ([results](eval/results/README.md)). The private corpus stays on BM25:
  embedding would send its text to Vertex AI.
- **Where the data lives.**
  - Each image carries one corpus at one commit: the SQLite index, built and embedded by the deploy workflow.
    Search, line reads and the verifier's checks read that file, in-process, so they add no network round trips
    to an answer.
  - The same index is loaded into BigQuery. The SQL agent's queries run there (`RL_SQL_BACKEND=bigquery`). The
    service account can only read the dataset, and each query is dry-run and refused unless BigQuery classifies
    it as a single SELECT. `bigquery.vector_search` runs `VECTOR_SEARCH` over the same vectors.
  - At startup the service checks that BigQuery holds the same commit as its image.
- **Service (`researchledger/service.py`).** Cloud Run, with `POST /ask`, `POST /search`, `GET /healthz`, and an
  MCP endpoint at `/mcp/` (tools `search`, `read_lines`, `ask`). Cloud Run IAM is the only access path: there are no
  unauthenticated invokers. From Claude Code: `gcloud run services proxy researchledger-prod --port 8080`, then
  `claude mcp add --transport http researchledger http://localhost:8080/mcp/`.
- **Tracing.** ADK's OpenTelemetry spans (agents, model calls, tool calls) are exported to Cloud Trace.
- **Infrastructure (`infra/`, Terraform).**
  - APIs, Artifact Registry, the BigQuery dataset, and staging and production Cloud Run services.
  - Two service accounts: the runtime one (Gemini, read-only BigQuery, traces) and the deployer.
  - Workload Identity Federation for GitHub Actions, limited to this repository's `main` branch.
  - There are no keys or secrets anywhere, so there is no Secret Manager entry to create.
- **CI (`.github/workflows/`).**
  - `ci.yml` runs the unit tests on every push and PR, with no network.
  - `deploy.yml` (manual, from `main`) runs these steps:
    1. ingests, embeds and exports the index;
    2. builds the image and deploys it to staging;
    3. grades the whole public evaluation set against staging, which also measures latency end to end on Cloud
       Run;
    4. promotes to production only if every gate passes.
- **Latency work (no paid capacity).**
  - Per-request timeouts (a hung call is retried rather than waited out).
  - Low thinking for the verifier.
  - Tool-call budgets for the sub-agents.
  - A computed claim missing its SQL gets the query the SQL agent actually ran, so it no longer costs a retry.

## Plan

1. Evaluation sets and thresholds, approved before code: private corpus (approved 17 Oct 2026), then the public
   demo corpus (Marin).
2. Local ingestion and retrieval, measured against both evaluation sets.
3. Verifier and agents (ADK, Gemini).
4. GCP: BigQuery, Cloud Run, Terraform, CI, MCP endpoint, tracing.
5. Evaluation report with every result, including failures (per item for the demo corpus, in aggregate for the
   private corpus); field notes on friction in the stack (`docs/FIELD_NOTES.md`).
