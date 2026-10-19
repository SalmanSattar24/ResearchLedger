# Hand check of the judge: answers-marin-20261018T045520.json

Judge model: gemini-2.5-pro.

How to mark: you are checking the judge, not the system. For each line, replace `[ ]` with `[y]` if you
agree with the judge or `[n]` if you don't, and add a few words after an `[n]`.

- **Fact lines:** read the answer above. Is the fact stated in it (by meaning, not wording)? The judge's call is shown.
- **Claim lines:** read the cited text shown under the claim. Does that text support the claim? The judge's call is
  shown.

When done, the `[n]` marks are the disagreements; THRESHOLDS.md asks for them to be reported with the run (in
`eval/results/README.md`). There is no pass mark: they show how far the judge's accuracy figures can be trusted.

## C02 (claim)
**Question:** Check: 'a z-loss penalty fixed the training loss creeping up during Marin 8B's deep cooldowns'

**Answer:** The claim is supported. During Marin 8B's deep cooldown experiments ("Raccoon" and "Spoonbill"), steady/slow increases in training loss were observed during cooldown at low learning rates, and this issue was fixed by adding a z-loss penalty of 1e-4 on the final logits.

- [ ] fact `the lm_head was exploding`: judge says **NOT stated** (numbers found in the answer)
- [ ] fact `z-loss penalty of 1e-4 on the final logits`: judge says **stated** (numbers found in the answer)
- [ ] claim `A graph depicts a slow increase in training loss during the cooldown for Spoonbill.`: judge says **supported**
  - cited `docs/reports/marin-8b-retro.md:453-453`:
    > ![graph depicting the slow increase in training loss during the cooldown for spoonbill](../images/marin-8b-spoonbill-loss.png)
- [ ] claim `The team fixed the loss increase during the Spoonbill cooldown by adding a z-loss penalty of 1e-4 on the final logits.`: judge says **supported**
  - cited `docs/reports/marin-8b-retro.md:459-459`:
    > We fixed this by adding a z-loss penalty of 1e-4 on the final logits.
- [ ] claim `In the "Raccoon" and "Spoonbill" deep cooldowns, steady loss increases were observed at low learning rate, prompting the team to impose a z-loss penalty of 1e-4 on the final logits for Phase 5 (Starling).`: judge says **supported**
  - cited `docs/reports/marin-8b-retro.md:550-551`:
    > Based on our findings in the "Raccoon" and "Spoonbill" deep cooldowns (where we observed steady loss increases at low
    > learning rate), we imposed a z-loss penalty of 1e-4 on the final logits.

## C04 (claim)
**Question:** Check: 'Marin 32B (Mantis) is the best open-weights base model in its comparison'

**Answer:** The claim is partly supported. In terms of mean rank across the evaluated models, Marin 32B (Mantis) is the best with a mean rank of 3.05. However, in terms of average accuracy, it is not the best open-weights base model: it surpasses OLMo 32B (+2.0, better on 14 of 19) and is roughly on par with Gemma 3 27B PT (+0.1, better on 9 of 19), but trails behind Qwen 2.5 32B Base (-2.8, better on 8/19) and NVIDIA Nemotron Nano 12B v2 Base (-3.4, better on 10/19).

- [ ] fact `best mean rank, 3.05`: judge says **stated** (numbers found in the answer)
- [ ] fact `Qwen 2.5 32B Base has a higher mean reciprocal rank (0.54 vs 0.44)`: judge says **NOT stated** (numbers missing in the answer)
- [ ] claim `In terms of mean rank among open weights base models, Marin 32B (Mantis) fares quite well with a mean rank of 3.05, making it the best of these models (lower is better).`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:457-457`:
    > In terms of mean rank, Marin fares quite well among other open weights base models:
  - cited `docs/reports/marin-32b-retro.md:462-462`:
    > | **Marin 32B (Mantis)**               |  **3.05** |                 0.44 |
  - cited `docs/reports/marin-32b-retro.md:468-468`:
    > Overall, the Mantis 32B model does quite well! In terms of mean rank, it is the best of these models (lower is better).
- [ ] claim `In terms of average accuracy, Marin 32B surpasses OLMo 32B (+2.0, better on 14 of 19) and is more or less on par with Gemma 3 27B PT (+0.1, better on 9 of 19).`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:471-472`:
    > In terms of average accuracy, it manages to surpass OLMo 32B (+2.0, better on 14 of 19), the previous best open source base model,
    > and is more or less on par with Gemma 3 27B PT (+0.1, better on 9 of 19).
- [ ] claim `In terms of average accuracy, Marin 32B is a bit behind Qwen 2.5 32B Base (-2.8, better on 8/19) and NVIDIA Nemotron Nano 12B v2 Base (-3.4, better on 10/19).`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:473-473`:
    > It is a bit behind Qwen 2.5 32B Base (-2.8, better on 8/19) and NVIDIA Nemotron Nano 12B v2 Base (-3.4, better on 10/19).

## C05 (claim)
**Question:** Check: 'in the Ocelot phase the 8B batch size was increased by 50%'

**Answer:** The claim is partly supported. While the overview of training phases in the Marin 8B retrospective states that in the Ocelot phase "to better utilize the hardware, we increased our batch size 50%", the detailed section on Phase 2 (Ocelot) Adjusted Hyperparameters contradicts this by stating: "To better utilize the hardware, we increased our batch size by 3x, to 12Mi tokens at around 2.77e12 tokens."

- [ ] fact `the record conflicts: the phase summary says 50%, the Ocelot section says 3x, to 12Mi tokens, from 4Mi`: judge says **stated** (numbers missing in the answer)
- [ ] claim `In the summary of training phases for the Marin 8B run, the Ocelot phase notes that to better utilize the hardware, the batch size was increased 50%.`: judge says **supported**
  - cited `docs/reports/marin-8b-retro.md:113-113`:
    > - *Ocelot (DCLM WSD Phase)*: We were given access to a v4-2048 slice and moved to that. To better utilize the hardware, we increased our batch size 50%. We also switched from WSD-S to WSD. We kept the learning rate high through 3.78T tokens.
- [ ] claim `In the detailed Adjusted Hyperparameters section for Phase 2: Ocelot (EMA Phase), it states that to better utilize the hardware, the batch size was increased by 3x, to 12Mi tokens at around 2.77e12 tokens.`: judge says **supported**
  - cited `docs/reports/marin-8b-retro.md:242-242`:
    > To better utilize the hardware, we increased our batch size by 3x, to 12Mi tokens at around 2.77e12 tokens.

## C06 (claim)
**Question:** Check: 'GSM8k contamination inflated Marin 32B's GSM8K score'

**Answer:** The claim is unsupported. Rather than inflating performance, GSM8k contamination caused Marin 32B to perform much worse on standard evaluations. Under the standard LM Eval Harness prompt, the model was ~22 points worse than the weakest baseline because Dolmino's GSM8k used OLMes formatting rather than LM Eval's default, leading to dramatically increased surprisal on the original prompt structured tags.

- [ ] fact `the contamination made it worse: about 22 points below the weakest baseline`: judge says **stated** (numbers found in the answer)
- [ ] claim `Under the standard LM Eval Harness prompt, Marin 32B was ~22 points worse than the weakest baseline on GSM8k.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:337-338`:
    > The run was broadly strong versus OLMo 2 32B, with one extreme exception: GSM8k.
    > Under the standard LM Eval Harness prompt, the model was ~22 points worse than the weakest baseline.
- [ ] claim `The root cause was determined to be accidental contamination from Dolmino math data including GSM8k test items cached during the Bison cooldown.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:341-343`:
    > We determined the root cause to be contamination. That is, we (accidentally) cheated but we cheated badly.
    > Our [Dolmino](https://huggingface.co/datasets/allenai/dolmino-mix-1124/tree/main/data/math) math bundle included GSM8k test items in a `test.json`.
    > Although we later updated preprocessing to drop `test.json`, the dataset had already been cached on the cluster, introducing contamination for GSM8K on the Bison cooldown.
- [ ] claim `Because Dolmino's GSM8k used OLMes formatting instead of LM Eval's default, contamination resulted in dramatically increased surprisal on the original prompts' structured tags, causing the model to perform much worse rather than showing the expected improvement.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:345-349`:
    > Dolmino’s GSM8k uses OLMes formatting, not LM Eval’s default.
    > Therefore, rather than the expected improvement in results from training on the test,
    > contamination made our model have dramatically increased surprisal on the original prompts structured tags (e.g., `16-8=<<16-7=9>>9`) that don’t appear in the contaminated data.
    > This high surprisal seemed to cause our model to perform much worse than it did on the same questions with those tags removed.

## L03 (lookup)
**Question:** What was the data mix in the first phase (Kestrel) of the 8B run?

**Answer:** In the first phase (Kestrel) of the 8B run, the data mix used was the DCLM 7B mixture in ratios roughly proportional to token count: 92.6% DCLM Baseline, 6.1% StarCoder Data, and 1.3% Proofpile 2.

- [ ] fact `DCLM Baseline 92.6%`: judge says **stated** (numbers found in the answer)
- [ ] fact `StarCoder Data 6.1%`: judge says **stated** (numbers found in the answer)
- [ ] fact `Proofpile 2 1.3%`: judge says **stated** (numbers found in the answer)
- [ ] claim `At the beginning of the run, the DCLM 7B mix was used in ratios roughly proportional to token count.`: judge says **supported**
  - cited `docs/reports/marin-8b-retro.md:151-152`:
    > At the beginning, we decided to use the DCLM 7B mix in
    > ratios roughly proportional to token count. (DCLM 7B was, at the time, the best open source model.)
- [ ] claim `The Kestrel data mix consisted of 92.6% DCLM Baseline, 6.1% StarCoder Data, and 1.3% Proofpile 2.`: judge says **supported**
  - cited `docs/reports/marin-8b-retro.md:156-160`:
    > | Dataset                                                                          | Percentage |
    > |----------------------------------------------------------------------------------|------------|
    > | [DCLM Baseline](https://huggingface.co/datasets/mlfoundations/dclm-baseline-1.0) | 92.6%      |
    > | [StarCoder Data](https://huggingface.co/datasets/bigcode/starcoderdata)          | 6.1%       |
    > | [Proofpile 2](https://huggingface.co/datasets/EleutherAI/proof-pile-2)           | 1.3%       |

## S05 (superseded)
**Question:** Which cooldown produced the final Marin 32B?

**Answer:** The final Marin 32B was produced by Phase 4b: the Mantis Cooldown (`exp1529_32b_mantis_cooldown`). It served as the second midtraining cooldown attempt after the initial Bison cooldown (`exp1529_32b_bison_cooldown`), addressing shuffling pathologies and GSM8k contamination with a Feistel-based shuffle and a cleaner math mix.

- [ ] fact `Mantis`: judge says **stated** (numbers found in the answer)
- [ ] fact `the earlier Bison cooldown was abandoned after its GSM8k contamination and shuffle phase shift`: judge says **stated** (numbers found in the answer)
- [ ] claim `Phase 4a was the Bison Cooldown (`exp1529_32b_bison_cooldown`) and Phase 4b was the Mantis Cooldown (`exp1529_32b_mantis_cooldown`).`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:56-57`:
    > - Phase 4a \- Bison Cooldown: [#1529](https://github.com/marin-community/marin/issues/1529) [`exp1529_32b_bison_cooldown`](https://github.com/marin-community/marin/blob/ee163702c5bc71c9bbba3238db84b6ee86e826a7/experiments/tootsie/exp1529_32b_bison_cooldown.py)
    > - Phase 4b \- Mantis Cooldown: [#1681](https://github.com/marin-community/marin/issues/1681) [`exp1529_32b_mantis_cooldown`](https://github.com/marin-community/marin/blob/ee163702c5bc71c9bbba3238db84b6ee86e826a7/experiments/tootsie/exp1529_32b_mantis_cooldown.py)
- [ ] claim `The first midtraining attempt (Bison) exposed two issues, which the second attempt (Mantis) fixed.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:276-276`:
    > The first attempt (*Bison*) mirrored our [Starling](./marin-8b-retro.md#phase-5-starling-second-cooldown)-style cooldown and exposed two issues; the second (*Mantis*) fixed them.
- [ ] claim `GSM8k contamination and shuffling pathologies from a linear congruential-driven permutation were addressed in the 'Mantis' cooldown with a Feistel-based shuffle and a cleaner math mix.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:33-33`:
    > Later, during cooldown, we uncovered GSM8k contamination (from a cached Dolmino bundle) and shuffling pathologies from a linear congruential-driven permutation. Both issues were addressed in the "Mantis" cooldown with a Feistel-based shuffle and a cleaner math mix.
- [ ] claim `Attempt 2 — Mantis Cooldown restarted from the 160k checkpoint with a Feistel shuffle and cleaner math mix.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:371-379`:
    > #### Attempt 2 — Mantis Cooldown
    > - Issue: [#1681](https://github.com/marin-community/marin/issues/1681)
    > - Experiment: [`exp1529_32b_mantis_cooldown`](https://github.com/marin-community/marin/blob/ee163702c5bc71c9bbba3238db84b6ee86e826a7/experiments/tootsie/exp1529_32b_mantis_cooldown.py)
    > We restarted from 160k with two major changes:
    > - Feistel shuffle. Switched from linear permutation to a more robust Feistel‑based shuffle.
    > - Cleaner math mix. Replaced Dolmino math with [MegaMath](https://arxiv.org/abs/2504.02807) splits and later added [Common Pile](https://arxiv.org/abs/2506.05209)'s [Stack V2 EDU](https://huggingface.co/datasets/common-pile/stackv2_edu_filtered) Python (around 174k), redistributing the HQ budget accordingly.

## S06 (superseded)
**Question:** Has phase 2 of the hero mixture been deployed?

**Answer:** As recorded on September 14, 2026, the initial mixture is in use, and phases 2 and 3 are planned in PR #9162; the log does not record them as deployed. Phase 2 (Main mixture) is planned for step 108,000 (~27.7%).

- [ ] fact `no: as recorded on September 14, 2026, the initial mixture is in use`: judge says **NOT stated** (numbers found in the answer)
- [ ] fact `phases 2 and 3 are planned in PR #9162`: judge says **stated** (numbers found in the answer)
- [ ] claim `As recorded on September 14, 2026, the initial mixture is in use.`: judge says **supported**
  - cited `docs/reports/hero-mixture-log.md:7-7`:
    > As recorded on September 14, 2026, the initial mixture is in use. Phases 2 and 3 are planned in
- [ ] claim `Phases 2 and 3 are planned in PR #9162; this log does not record them as deployed.`: judge says **supported**
  - cited `docs/reports/hero-mixture-log.md:7-9`:
    > As recorded on September 14, 2026, the initial mixture is in use. Phases 2 and 3 are planned in
    > [PR #9162](https://github.com/marin-community/marin/pull/9162); this log does not
    > record them as deployed. Append future mixture changes with their effective step
- [ ] claim `Phase 2 (Main mixture) is planned for step 108,000 (~27.7%).`: judge says **supported**
  - cited `docs/reports/hero-mixture-log.md:20-20`:
    > ## Phase 2 — Main mixture · planned step 108,000 (~27.7%)

## S07 (superseded)
**Question:** Is the grugformer-vs-hackable-125m experiment still current?

**Answer:** No, the grugformer-vs-hackable-125m experiment is not current. Its status is deleted, its purpose was a historical head-to-head comparison, and it was superseded by 8d752a775 (a template-first workflow centered on experiments/grug/base/).

- [ ] fact `no, it is deleted`: judge says **stated** (numbers found in the answer)
- [ ] fact `superseded by 8d752a775, the template-first workflow centred on experiments/grug/base/`: judge says **stated** (numbers found in the answer)
- [ ] claim `The status of the grugformer-vs-hackable-125m experiment is deleted.`: judge says **supported**
  - cited `docs/reports/grug-archive.md:72-76`:
    > ### grugformer-vs-hackable-125m
    > - Path: `experiments/speedrun/grugformer_vs_hackable_125m/grugformer_vs_hackable_125m.py`
    > - Introduced: 5efe76834
    > - Last known-good: 5efe76834
    > - Status: deleted
- [ ] claim `The purpose of grugformer-vs-hackable-125m was a historical head-to-head comparison.`: judge says **supported**
  - cited `docs/reports/grug-archive.md:72-77`:
    > ### grugformer-vs-hackable-125m
    > - Path: `experiments/speedrun/grugformer_vs_hackable_125m/grugformer_vs_hackable_125m.py`
    > - Introduced: 5efe76834
    > - Last known-good: 5efe76834
    > - Status: deleted
    > - Purpose: historical head-to-head comparison.
- [ ] claim `The grugformer-vs-hackable-125m experiment was superseded by 8d752a775 — template-first workflow centered on experiments/grug/base/.`: judge says **supported**
  - cited `docs/reports/grug-archive.md:72-78`:
    > ### grugformer-vs-hackable-125m
    > - Path: `experiments/speedrun/grugformer_vs_hackable_125m/grugformer_vs_hackable_125m.py`
    > - Introduced: 5efe76834
    > - Last known-good: 5efe76834
    > - Status: deleted
    > - Purpose: historical head-to-head comparison.
    > - Superseded by: 8d752a775 — template-first workflow centered on `experiments/grug/base/`.

## T02 (table)
**Question:** How many datasets in the 32B Mantis cooldown mixture have a share above 5%?

**Answer:** In the 32B Mantis cooldown mixture table, 6 datasets have a share above 5%: `nemotron_cc/medium` (21.49%), `nemotron_cc/hq_synth` (17.29%), `nemotron_cc/medium_low` (9.79%), `nemotron_cc/hq_actual` (5.81%), `megamath/web` (5.57%), and `nemotron_cc/medium_high` (5.24%).

- [ ] fact `6`: judge says **stated** (numbers found in the answer)
- [ ] claim `There are 6 datasets in the Mantis cooldown mixture with a percentage share above 5%.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:383-407`:
    > | Dataset                     | Percentage |
    > |----------------------------|------------|
    > | nemotron_cc/medium         | 21.49%     |
    > | nemotron_cc/hq_synth       | 17.29%     |
    > | nemotron_cc/medium_low     | 9.79%      |
    > | nemotron_cc/hq_actual      | 5.81%      |
    > | nemotron_cc/medium_high    | 5.24%      |
    > | nemotron_cc/low_actual     | 4.46%      |
    > | nemotron_cc/low_synth      | 3.99%      |
    > | megamath/web               | 5.57%      |
    > | arxiv_markdownified        | 4.54%      |
    > | megamath/text_code_block   | 4.24%      |
    > | dolmino/pes2o              | 4.54%      |
    > | megamath/web_pro           | 1.27%      |
    > | megamath/translated_code   | 0.61%      |
    > | megamath/qa                | 0.59%      |
    > | finemath-3-plus            | 2.66%      |
    > | dolmino/flan               | 2.66%      |
    > | stackexchange_custom       | 1.34%      |
    > | dolmino/stackexchange      | 1.34%      |
    > | starcoderdata              | 1.59%      |
    > | proofpile_2                | 0.35%      |
    > | wikipedia_markdown         | 0.29%      |
    > | dolmino/wiki               | 0.29%      |
    > | medu_science_qa            | 0.09%      |
- [ ] claim `In the 32B Mantis cooldown mixture, nemotron_cc/medium has a share of 21.49%, nemotron_cc/hq_synth has 17.29%, nemotron_cc/medium_low has 9.79%, nemotron_cc/hq_actual has 5.81%, nemotron_cc/medium_high has 5.24%, and megamath/web has 5.57%.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:385-392`:
    > | nemotron_cc/medium         | 21.49%     |
    > | nemotron_cc/hq_synth       | 17.29%     |
    > | nemotron_cc/medium_low     | 9.79%      |
    > | nemotron_cc/hq_actual      | 5.81%      |
    > | nemotron_cc/medium_high    | 5.24%      |
    > | nemotron_cc/low_actual     | 4.46%      |
    > | nemotron_cc/low_synth      | 3.99%      |
    > | megamath/web               | 5.57%      |

## W05 (why)
**Question:** Why did the 32B run switch to the Qwen3 backbone?

**Answer:** The 32B run switched to the Qwen3 32B backbone because the team concluded that stabilizing a 32B Llama without architectural help was not feasible under their constraints after encountering a loss-instability episode around 70k–80k steps. The Qwen3 32B backbone adds QK-Norm in attention, which resolved the instability and stabilized training.

- [ ] fact `at 80k steps spikes were unavoidable even with update clipping`: judge says **NOT stated** (numbers found in the answer)
- [ ] fact `QK-Norm`: judge says **stated** (numbers found in the answer)
- [ ] fact `warm-started from the 80k Llama weights`: judge says **NOT stated** (numbers found in the answer)
- [ ] claim `The team concluded that stabilizing a 32B Llama without architectural help wasn't feasible under their constraints.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:247-247`:
    > At this point we concluded that stabilizing a 32B Llama without architectural help wasn’t feasible under our constraints. We switched to Qwen3 32B, which adds QK‑Norm in attention, and warm‑started from the 80k Llama weights. This preserved useful signal in embeddings and MLPs while letting the normalized attention heads relearn.
- [ ] claim `A loss-instability episode occurred around 70k–80k steps in exp1295_32b that was ultimately resolved by introducing QK-Norm via a switch to the Qwen3 32B backbone.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:32-32`:
    > The notable exception was a loss-instability episode around 70k–80k steps in `exp1295_32b` that we ultimately resolved by introducing QK-Norm via a switch to the Qwen3 32B backbone.
- [ ] claim `The switch to Qwen3 32B adds QK-Norm in attention.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:247-247`:
    > At this point we concluded that stabilizing a 32B Llama without architectural help wasn’t feasible under our constraints. We switched to Qwen3 32B, which adds QK‑Norm in attention, and warm‑started from the 80k Llama weights. This preserved useful signal in embeddings and MLPs while letting the normalized attention heads relearn.
- [ ] claim `Switching to Qwen3 32B (QK-Norm) stabilized the loss and allowed training to recover.`: judge says **supported**
  - cited `docs/reports/marin-32b-retro.md:45-45`:
    > | 3     | 80,000 → 160,000 | 2.684      | Switch to Qwen3 32B (QK-Norm)                      | Loss stabilized; training recovered               |
