# Evaluation set changelog

Every change to `eval/questions.yaml` or `eval/THRESHOLDS.md` is logged here with the reason, before and after
approval. (The private research corpus's set keeps its own changelog in its private repository.)

## 2026-10-17 (v0.1 draft, public demo corpus Marin at 5e12684)

- **Created** `eval/questions.yaml`: 41 items (12 lookup, 8 why, 8 superseded, 7 claim, 3 table, 3 safety), the same
  type mix as the private set, so the same required counts apply. The sources are the 8B and 32B retrospectives, the
  hero mixture log, the grug archive and the daily ferry log.
- **Checked by script before review:** every gold file and line range exists at 5e12684, and every number in
  `must_include` and `must_not` appears in its gold lines. The table answers were computed from the parsed tables:
  T01 Dolmino FLAN and Dolmino Math, T02 6, T03 13 of 19. Phrases judged by meaning were checked by reading only.
- **C05 deliberately tests a contradiction in the record:** the 8B phase summary (line 113) says the Ocelot batch
  size rose 50%, while the Ocelot section (line 242) says 3x, from 4Mi to 12Mi tokens.

## 2026-10-17 (v0.1 approved by the researcher)

- **Approved** `eval/questions.yaml` v0.1 as drafted above.
- **Ingestion rule changed (README, data boundary), so the corpus can be ingested:** URL query tokens are now
  redacted and each redaction logged (file, line, parameter name; never the value); ingestion still fails on real
  secrets and on images or data files. Reason: line 426 of `docs/reports/marin-8b-retro.md` contains a WandB report link
  with an `accessToken=` parameter, and under the old rule (fail on any token pattern) Marin could not be ingested.
  Item X01 tests the new rule: the token must never be produced.

## 2026-10-17 (after approval: gold ranges widened, researcher-approved)

- **Rule:** gold ranges now aim to list every *current* passage that states an item's fact, not only the first one
  found. Reason: step 2's retrieval often found a correct statement of the fact in another document, which the
  citation-recall gate counted as a miss.
- **Procedure:**
  1. Candidates were proposed by plain text search (`researchledger/gold.py`): exact numbers plus distinctive words,
     paragraphs and table rows, archived paths excluded. The retriever was not used, so the new gold does not favour
     it.
  2. Each candidate was read and narrowed to the exact lines.
  3. The researcher approved each addition before it was applied.
- **Added (Marin, 4 ranges):**
  - L02: `index.md:68` (new alias IX), fact [1].
  - W04: `marin-8b-retro.md:297-299`, facts [1, 2].
  - C02: `marin-8b-retro.md:550-551`, fact [2].
  - S02: `marin-32b-retro.md:378`, fact [1]. The line itself does not say "Mantis"; its section heading does.
- **Rejected after reading:**
  - L12 `marin-8b-retro.md:550-551`: describes the Starling z-loss, not Spoonbill's.
  - T01 `marin-32b-retro.md:312-313`: says Dolmino math was upsampled 2x "the same as" the 8B Starling mix, which
    lists 10x. This is a second contradiction in the record, noted as a possible future claim item.
- **Scores before and after** are in `eval/results/README.md`.
