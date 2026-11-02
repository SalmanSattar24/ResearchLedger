# ResearchLedger public corpus Evidence Explorer

This demo replaces synthetic fixtures with a real pinned public Marin research corpus and ResearchLedger's Python retrieval and verification modules. It is separate from the existing ADK/Vertex/Cloud Run service. It does not imply that ResearchLedger's production evaluation gates have passed.

**Level one works without an API key.** Ingestion uses the existing leakage scanner and pinned Git objects. The demo runs the existing BM25 retriever and deterministic citation/number/quote checker. It displays exact retrieved excerpts and pinned GitHub source links. It labels those excerpts as retrieval results, not semantically verified generated answers. No-match queries abstain.

**Level two is opt-in.** A Gemini Developer API adapter generates up to four cited claims, checks them with the existing deterministic verifier, then requests a separate model support assessment. All claims need a complete affirmative support result. Failure, malformed/missing verdicts or out-of-context citations yield abstention. The final prose is constructed only from checked claims. This is a bounded two-call demo flow, not the complete ADK tool orchestration, SQL-agent or hybrid-vector service.

## Run locally

From the ResearchLedger repository:

```sh
python -m pip install -e '.[demo,dev]'
python scripts/build_demo_bundle.py
python -m researchledger.demo
```

Open `http://127.0.0.1:8765`. Building the corpus needs Git/network on the first run. Once built, keyword mode needs no external service. The import ZIP is `.cache/evidence-demo-bundle/researchledger-public-demo.zip`.

For the standalone ZIP: extract into a dedicated workspace, run `python3 release.py build`, then `python3 release.py serve`. The build uses the installed official `uv` package manager to install the pinned Pydantic dependency. `release.py check` verifies every bundled hash, corpus counts, retrieval, abstention and rejected-claim behavior without making model calls. Startup checks the manifest again. The server honors `PORT` (default 5000), exposes `/healthz`, bounds concurrent connections and times out incomplete client requests. The ZIP contains only an explicit code allowlist, the public index, license and manifests; no environment files, credentials, private corpora, cloud configuration or research artifacts.

## Enable generated answers

Use an operator-owned Gemini API key from a project **without active paid billing**. The app cannot infer a key's billing status. Store these environment variables as server-side Replit Secrets or a local process environment, never frontend code or a committed file:

- `GEMINI_API_KEY`: your existing Gemini Developer API key.
- `RL_DEMO_FREE_TIER_CONFIRMED=1`: set only after checking that project's current free tier, model access and billing status.

The adapter is fixed to `gemini-3.5-flash-lite`, whose standard free input/output pricing was checked on November 1, 2026. It makes no search-grounding, embedding or other tool requests. If the model becomes unavailable, it fails closed; there is no automatic model substitution. Do not use Replit AI Integrations, Vertex credentials or enable billing to resolve an error.

Usage is recorded in SQLite under `.cache/demo-usage.sqlite`: at most 20 model calls per UTC day and four per rolling minute for requests sharing that retained ledger, with two calls reserved before a generated question starts. Failed calls still count. The allowance survives a process restart only while that file is retained. A redeployment, filesystem reset or separate autoscale replica can start a separate allowance; this is not a durable account-wide cap. The prepared deployment uses one maximum server. Google's project quotas remain the external limit. These limits reduce use but do not prove zero cost on a billing-enabled project.

Model keys are only sent to Google's fixed HTTPS API endpoint, via a header. The browser never receives them. Public excerpts and user questions are sent to Google in generated mode; Google's free-tier data-use terms apply. Do not enter private research or credentials as questions.

## Replit integration

The standalone server serves both UI and API on one port. The existing React demo may instead proxy `/api/meta` and `/api/ask` to this server on an internal port; never put the key or call Gemini directly in React. Keep the synthetic fixture demo separate and labeled if retained. Publishing is a separate operator action. Replit Starter's current one-free-app publication and 30-day expiration limit apply; confirm the actual account allowance before publication. No paid upgrade is required by this code.

The browser UI uses `/evidence-api/meta` and `/evidence-api/ask` to avoid collisions with a host workspace's generic `/api` routing. The standalone server also accepts the original `/api` aliases for local clients.

For the already-created Replit React workspace, `configure_replit_preview.py` installs a reversible Vite development bridge: it backs up the original Vite config, starts Python on loopback port 5002, and forwards the existing preview requests to it. Run the helper from the workspace root after extracting into `evidence-explorer-integrated-20261101` and installing requirements into that folder's `vendor/` with `uv pip install --target .../vendor -r .../requirements.txt`. It preserves the prototype files and never configures a key, billing or publication. It deliberately refuses an unexpected Vite config or an existing conflicting backup. Restart the development preview after a server-side Secret change so Python inherits it.

Production uses the standalone Python server directly, not Vite or the synthetic prototype. From the existing workspace root, run `python3 evidence-explorer-integrated-20261101/configure_replit_release.py`. It backs up `.replit`, replaces only its deployment section with the release build/serve commands, and preserves development workflows. This prepares configuration; it does not publish. Keep the deployment on the available free allowance with one maximum server; inspect the final Replit summary before publishing. Both `GEMINI_API_KEY` and `RL_DEMO_FREE_TIER_CONFIRMED=1` must be present in the deployment environment for generated mode. Retrieval works when either is absent.

For Agent workspaces using the application router, also run the extracted `configure_replit_artifact_release.py` from the workspace root. These workspaces publish the web artifact's `.replit-artifact/artifact.toml`, which can override root deployment commands. The helper switches that artifact from static prototype output to Python build/run, preserving identity, routes, port and development startup. A public smoke check is essential: metadata must show nine real documents and 179 chunks.

## What to inspect

1. Ask about QK-Norm in the 32B run; inspect the commit and line links.
2. Ask an unindexed nonsense topic; confirm no fabricated answer.
3. Toggle the unsupported-numeric-claim test; confirm a separate rejected candidate and blocked overall test status. This injects invented test text only, never into the final accepted answer.
4. Without secrets, generated mode must be disabled while retrieval still works.
5. With a confirmed free-tier key, inspect a generated answer and its two verification stages. Check failure on quota, invalid key, incomplete verifier output and unsupported claims.

Deterministic checks validate provenance and literal values, not truth or relevance. Model support checks are fallible, and keyword retrieval can miss relevant passages. The backend deliberately excludes arbitrary SQL and hybrid embeddings in this demo. Existing service and cloud files are not changed or deployed.

## Sources and license

Public text is from `https://github.com/marin-community/marin`, commit `5e12684c85eac9295514a4c8cdbfee0a55ad497c`, limited to `docs/reports/` and `docs/experiments/`. The ingestion process redacts URL credentials and refuses detected secrets or unsupported content. The bundle includes upstream Apache-2.0 license/NOTICE when present; corpus and bundle manifests retain provenance and hashes.

API and quota references: https://ai.google.dev/api/generate-content · https://ai.google.dev/gemini-api/docs/pricing · https://docs.replit.com/billing/plans/starter-plan
