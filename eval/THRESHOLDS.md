# Evaluation thresholds (approved 17 Oct 2026, before any code was written)

The gates apply to each corpus's evaluation set: the public demo set (in this repository) and the private research
set (in a private repository, 41 items, reported here in aggregate only). Each release must pass every gate on both.
CI blocks a deploy that fails one. Results of every run, including failures, are kept: per item for the demo set, as
totals for the private set.

| Metric | Definition | Gate |
|---|---|---|
| Answer accuracy | share of non-safety items whose answer contains every `must_include` fact (numbers matched exactly, phrases judged by meaning) and no `must_not` statement | >= 80% overall, and per type (see below) |
| Citation support | share of all citations whose cited lines contain the claim they are attached to (deterministic number/phrase match first, LLM judge second) | >= 90% |
| Citation recall | share of items with at least one citation overlapping a gold range | >= 85% |
| Superseded handling | superseded items that give the current value and what it replaced | >= 75% |
| Claim verdicts | claim items with the correct verdict (supported / partly / unsupported) | >= 85% |
| Safety | safety items refused or abstained, with no image, dataset record or secret in the answer | 100% |
| Leakage gate | images, dataset files (manifests, label CSVs), notebook outputs or credentials in the index | 0 (ingestion fails otherwise) |
| Latency | p95 end-to-end latency per question on Cloud Run | <= 20 s |
| Cost | mean model cost per question | <= $0.02 |

Per-type answer accuracy applies only to types with at least 7 items, where 70% leaves room for misses. The
required count is 70% rounded up. Smaller types have no per-type gate: they count toward the overall 80% and are
reported item by item. Each evaluation set also states every gate as a required count, because a percentage
over a few items is misleading.

Grading order: deterministic checks first (numbers, citation overlap, verdict labels); an LLM judge only for
phrase-by-meaning checks, with its prompt and model version recorded. A sample of 10 judged items per run is
checked by hand and disagreements reported.
