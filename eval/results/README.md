# Evaluation results

Every run is kept, including the ones that made things worse. Per-item results are published only for the public
demo corpus. The private research corpus is reported as totals, with no item, file or commit named.

## Retrieval (step 2, keyword search only)

What is measured: for each non-safety item, whether the top-k retrieved chunks overlap one of its gold line ranges
(**recall@k**), which bounds the final citation-recall gate (>= 85%). A second, diagnostic measure, **evidence@k**,
counts items whose expected numbers all appear somewhere in the top-k chunks, wherever they come from. It is only
computed for items whose expected facts contain numbers.

Retriever: BM25 (k1 = 1.5, b = 0.75) over section-aware chunks of at most 30 lines; chunks include file path and
heading path. No embeddings yet. Hybrid search with Vertex AI embeddings comes in step 4.

### Runs on the public demo corpus (Marin at 5e12684, 38 non-safety items)

| Run | Change | recall@1 | recall@5 | recall@10 | MRR@10 | evidence@10 |
|---|---|---|---|---|---|---|
| `retrieval-marin-20261017T101056.json` | first baseline | 29/38 | 36/38 | 37/38 | 0.839 | not yet measured |
| `retrieval-marin-20261017T101704.json` | one chunk per table row (dropped) | 24/38 | 34/38 | 35/38 | 0.743 | 26/32 |
| `retrieval-marin-20261017T101906.json` | baseline again, with exact line maps | 29/38 | 36/38 | 37/38 | 0.839 | 31/32 |
| `retrieval-marin-20261017T195738.json` | same retriever, gold widened (4 ranges; see `eval/CHANGELOG.md`) | 29/38 | 36/38 | 37/38 | 0.839 | 31/32 |

The only miss at 10 is T02 (a table question). Table questions are meant for the SQL agent over parsed tables, not
for chunk retrieval.

### Private research corpus (41 items, 38 non-safety; aggregate only)

| Run | recall@1 | recall@5 | recall@10 | MRR@10 | evidence@5 | evidence@10 |
|---|---|---|---|---|---|---|
| first baseline | 10/38 | 19/38 | 24/38 | 0.374 | not yet measured | not yet measured |
| one chunk per table row (dropped) | 9/38 | 21/38 | 24/38 | 0.366 | 24/34 | 25/34 |
| baseline again, with exact line maps | 10/38 | 19/38 | 24/38 | 0.370 | 24/34 | 30/34 |
| same retriever, gold widened (60 ranges, 28 items) | 15/38 | 25/38 | 32/38 | 0.509 | 24/34 | 30/34 |

By type at 10, before and after widening: lookup 8/12 to 10/12, why 5/8 to 6/8, superseded 4/8 to 7/8, claim 4/7 to
6/7, table 3/3 to 3/3.

**Reading (before widening):** the gap between recall@10 (24/38) and evidence@10 (30/34) means retrieval usually finds the fact, but
often in a different document from the one the gold range names. The private record states many facts in several
places: trackers, handoff notes, status updates, plan versions and notebooks. Two things follow, and both are open:

1. The final citation-recall gate counts only citations that overlap a gold range. On this corpus, a correct answer
   that cites another document stating the same fact would count as a miss.
2. For superseded facts, citing an older document can be genuinely wrong. Preferring current documents over
   archived ones is part of the retrieval agent's job (step 3).

**Resolution (17 Oct 2026, researcher-approved):** gold ranges now aim to list every current passage that states an
item's fact.
- **How additions were found:** proposed by plain text search, not by the retriever, then read, narrowed to exact
  lines and approved one by one. Archived paths were never added. The procedure is in `eval/CHANGELOG.md`.
- **Effect:** the retriever and index are unchanged, so the rise in recall (24/38 to 32/38 at 10) is purely a change
  in what counts as a correct location. evidence@k, which does not depend on gold, is identical before and after.
- **Remaining gap:** 6 private items still miss at 10. On Marin the widening changed no rank.

**Caveat:** the dropped table-row experiment was judged on these same evaluation sets. There is no held-out set, so
any further tuning against them risks overfitting, and will be reported as such.

## Answers (step 3: agents and verifier, Marin only)

The private research corpus has not been run through the agents. That would send its text to Gemini, which waits
on the corpus owner's consent.

Each run answers all 41 items with the agents, then grades every gate in `eval/THRESHOLDS.md`. Numbers, citation
overlap, verdict labels and safety are graded deterministically; the judge model (`gemini-2.5-pro`, a different
family from the agents) grades only meaning. The judge prompts and models are stored in each results file.
Latency is measured locally, not yet on Cloud Run.

| Gate | Run 1 (`…032738`, 3.8-flash) | Run 3 (`…045520`, 3.7-flash) | Required |
|---|---|---|---|
| Answer accuracy, overall | 25/38 | 24/38 | >= 31 |
| lookup | 11/12 | 9/12 | >= 9 |
| why | 3/8 | 4/8 | >= 6 |
| superseded | 4/8 | 6/8 | >= 6 |
| claim | 4/7 | 2/7 | >= 5 |
| table (reported only) | 3/3 | 3/3 | no gate |
| Citation support | 91/92 | 100/101 | >= 90% |
| Citation recall | 35/38 | 36/38 | >= 33 |
| Superseded handling | 4/8 | 6/8 | >= 6 |
| Claim verdicts | 5/7 | 6/7 | >= 6 |
| Safety | 3/3 | 3/3 | 3/3 |
| Latency p95 (local) | 92.4 s | 52.3 s | <= 20 s |
| Cost per question (mean) | $0.0142 | $0.0104 | <= $0.02 |

Run 3 passes 8 of the 12 graded gates. It fails overall accuracy, "why" and claim accuracy, and latency.

**Between runs 1 and 3** (changes are general, but all were judged on this same set, so there is overfitting risk):
- The coordinator was told to answer completely and to use the set's own definition of "partly".
- The evidence pack keeps the chunk lines that match the question rather than only a chunk's first 600 characters.
- The agent model changed for latency: `gemini-3.8-flash` answered a one-word prompt in a median 22.8 s on 18 Oct
  2026, against 1.7 s for `gemini-3.7-flash` at the same price.

**Run 2** used `gemini-3.8-flash` with the run 3 prompts. It was stopped after 20 items, which took up to 822 s each;
the log is in `answers-marin-run2-stopped.log` and no results file was written.

**What the run 3 failures are:**
- **Fact left out (6):** L04, L07, L08, W06, C04, C07. The answer is right as far as it goes but omits a required
  fact or number.
- **Judge-only misses (6):** W02, W04, W05, S06, C02, C03. All numbers are present but the judge said a phrase was
  missing. Read by hand: 5 are genuine omissions; S06 is a judge false negative.
- **Exact number missing (2):** S03 and C05. The judge accepted the fact, but the answer did not write the number
  ("80,000", "from 4Mi").

The main weakness is completeness, not correctness: citation support is 99% and no answer asserted a forbidden
statement.

**Latency** in run 3: median 10.7 s, p90 25.9 s, p95 52.3 s. 25 of 41 questions took the fast path (one
coordinator call plus the verifier); delegation and verifier retries make up the tail. The shared Gemini quota
also returned 429s that needed backoff. Meeting 20 s at p95 likely needs fewer sequential model calls and dedicated
capacity (provisioned throughput or a priority tier), a cost decision for step 4.

**Hand check:** a seeded sample of 10 judged items from run 3 is in
`eval/review/hand-check-answers-marin-20261018T045520.md` for the researcher to mark.

**Judge cost** (not counted in the per-question gate): $0.57 in run 1 and $0.65 in run 3.
