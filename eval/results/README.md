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

The only miss at 10 is T02 (a table question). Table questions are meant for the SQL agent over parsed tables, not
for chunk retrieval.

### Private research corpus (41 items, 38 non-safety; aggregate only)

| Run | recall@1 | recall@5 | recall@10 | MRR@10 | evidence@5 | evidence@10 |
|---|---|---|---|---|---|---|
| first baseline | 10/38 | 19/38 | 24/38 | 0.374 | not yet measured | not yet measured |
| one chunk per table row (dropped) | 9/38 | 21/38 | 24/38 | 0.366 | 24/34 | 25/34 |
| baseline again, with exact line maps | 10/38 | 19/38 | 24/38 | 0.370 | 24/34 | 30/34 |

By type at 10 (final run): lookup 8/12, why 5/8, superseded 4/8, claim 4/7, table 3/3.

**Reading:** the gap between recall@10 (24/38) and evidence@10 (30/34) means retrieval usually finds the fact, but
often in a different document from the one the gold range names. The private record states many facts in several
places: trackers, handoff notes, status updates, plan versions and notebooks. Two things follow, and both are open:

1. The final citation-recall gate counts only citations that overlap a gold range. On this corpus, a correct answer
   that cites another document stating the same fact would count as a miss.
2. For superseded facts, citing an older document can be genuinely wrong. Preferring current documents over
   archived ones is part of the retrieval agent's job (step 3).

**Caveat:** the dropped table-row experiment was judged on these same evaluation sets. There is no held-out set, so
any further tuning against them risks overfitting, and will be reported as such.
