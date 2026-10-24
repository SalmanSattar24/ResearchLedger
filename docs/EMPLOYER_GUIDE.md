# Employer guide

## Project in one paragraph

ResearchLedger answers questions over research records with file-and-line citations, tracks superseded statements and checks whether claims are supported by evidence. Its reviewable engineering focus is provenance-aware retrieval and answer verification, not merely adding a chat interface to documents.

## Five-minute reading path

| Concern | Implementation |
|---|---|
| Controlled ingestion and data boundaries | [ingest.py](../researchledger/ingest.py), [leakage.py](../researchledger/leakage.py) |
| Retrieval and source grounding | [retrieve.py](../researchledger/retrieve.py), [tools.py](../researchledger/tools.py) |
| Agent orchestration | [agents.py](../researchledger/agents.py) |
| Claim checking | [verify.py](../researchledger/verify.py) |
| API / MCP boundary | [service.py](../researchledger/service.py) |
| Evaluation evidence | [thresholds](../eval/THRESHOLDS.md), [results](../eval/results/README.md) |

## What is implemented versus demonstrated

The README reports dated measurements and explicitly failed accuracy/latency gates. Read the actual evaluation record before repeating a number. Infrastructure definitions, service code and a deployment workflow do not by themselves prove a fully promoted, working production service; the README describes staging/promotion limitations.

## Local and paid paths

`python -m pip install -e ".[dev]"` and the repository's unit-test commands are the lightweight starting point. Ingestion can retrieve a pinned public corpus; model-answering, embedding, BigQuery operations and deployment are separate network/cloud paths. They can require credentials and incur charges. No cloud deployment, paid evaluation or API call was launched in this documentation refresh.

## Skills to discuss

Evidence provenance, retrieval evaluation, abstention, private/public corpus separation, deterministic checks around LLM output, least-privilege deployment design and measuring limitations honestly. Existing author/dependency/corpus attribution remains intact.
