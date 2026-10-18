# Hand check of the judge: answers-marin-20261018T045520.json

Judge model: gemini-2.5-pro. For each item, mark whether you agree with every judgement.

## C02 (claim)
Answer: The claim is supported. During Marin 8B's deep cooldown experiments ("Raccoon" and "Spoonbill"), steady/slow increases in training loss were observed during cooldown at low learning rates, and this issue was fixed by adding a z-loss penalty of 1e-4 on the final logits.
- fact `the lm_head was exploding`: numbers ok, judge says NOT stated. Agree? [ ]
- fact `z-loss penalty of 1e-4 on the final logits`: numbers ok, judge says stated. Agree? [ ]
- claim `A graph depicts a slow increase in training loss during the cooldown for Spoonbill.` cites docs/reports/marin-8b-retro.md:453-453: judge says supported. Agree? [ ]
- claim `The team fixed the loss increase during the Spoonbill cooldown by adding a z-loss penalty of 1e-4 on the final logits.` cites docs/reports/marin-8b-retro.md:459-459: judge says supported. Agree? [ ]
- claim `In the "Raccoon" and "Spoonbill" deep cooldowns, steady loss increases were observed at low learning rate, prompting the team to impose a z-loss penalty of 1e-4 on the final logits for Phase 5 (Starling).` cites docs/reports/marin-8b-retro.md:550-551: judge says supported. Agree? [ ]

## C04 (claim)
Answer: The claim is partly supported. In terms of mean rank across the evaluated models, Marin 32B (Mantis) is the best with a mean rank of 3.05. However, in terms of average accuracy, it is not the best open-weights base model: it surpasses OLMo 32B (+2.0, better on 14 of 19) and is roughly on par with Gemma 3 27B PT (+0.1, better on 9 of 19), but trails behind Qwen 2.5 32B Base (-2.8, better on 8/19) and NVIDIA Nemotron Nano 12B v2 Base (-3.4, better on 10/19).
- fact `best mean rank, 3.05`: numbers ok, judge says stated. Agree? [ ]
- fact `Qwen 2.5 32B Base has a higher mean reciprocal rank (0.54 vs 0.44)`: numbers MISSING, judge says NOT stated. Agree? [ ]
- claim `In terms of mean rank among open weights base models, Marin 32B (Mantis) fares quite well with a mean rank of 3.05, making it the best of these models (lower is better).` cites docs/reports/marin-32b-retro.md:457-457, docs/reports/marin-32b-retro.md:462-462, docs/reports/marin-32b-retro.md:468-468: judge says supported. Agree? [ ]
- claim `In terms of average accuracy, Marin 32B surpasses OLMo 32B (+2.0, better on 14 of 19) and is more or less on par with Gemma 3 27B PT (+0.1, better on 9 of 19).` cites docs/reports/marin-32b-retro.md:471-472: judge says supported. Agree? [ ]
- claim `In terms of average accuracy, Marin 32B is a bit behind Qwen 2.5 32B Base (-2.8, better on 8/19) and NVIDIA Nemotron Nano 12B v2 Base (-3.4, better on 10/19).` cites docs/reports/marin-32b-retro.md:473-473: judge says supported. Agree? [ ]

## C05 (claim)
Answer: The claim is partly supported. While the overview of training phases in the Marin 8B retrospective states that in the Ocelot phase "to better utilize the hardware, we increased our batch size 50%", the detailed section on Phase 2 (Ocelot) Adjusted Hyperparameters contradicts this by stating: "To better utilize the hardware, we increased our batch size by 3x, to 12Mi tokens at around 2.77e12 tokens."
- fact `the record conflicts: the phase summary says 50%, the Ocelot section says 3x, to 12Mi tokens, from 4Mi`: numbers MISSING, judge says stated. Agree? [ ]
- claim `In the summary of training phases for the Marin 8B run, the Ocelot phase notes that to better utilize the hardware, the batch size was increased 50%.` cites docs/reports/marin-8b-retro.md:113-113: judge says supported. Agree? [ ]
- claim `In the detailed Adjusted Hyperparameters section for Phase 2: Ocelot (EMA Phase), it states that to better utilize the hardware, the batch size was increased by 3x, to 12Mi tokens at around 2.77e12 tokens.` cites docs/reports/marin-8b-retro.md:242-242: judge says supported. Agree? [ ]

## C06 (claim)
Answer: The claim is unsupported. Rather than inflating performance, GSM8k contamination caused Marin 32B to perform much worse on standard evaluations. Under the standard LM Eval Harness prompt, the model was ~22 points worse than the weakest baseline because Dolmino's GSM8k used OLMes formatting rather than LM Eval's default, leading to dramatically increased surprisal on the original prompt structured tags.
- fact `the contamination made it worse: about 22 points below the weakest baseline`: numbers ok, judge says stated. Agree? [ ]
- claim `Under the standard LM Eval Harness prompt, Marin 32B was ~22 points worse than the weakest baseline on GSM8k.` cites docs/reports/marin-32b-retro.md:337-338: judge says supported. Agree? [ ]
- claim `The root cause was determined to be accidental contamination from Dolmino math data including GSM8k test items cached during the Bison cooldown.` cites docs/reports/marin-32b-retro.md:341-343: judge says supported. Agree? [ ]
- claim `Because Dolmino's GSM8k used OLMes formatting instead of LM Eval's default, contamination resulted in dramatically increased surprisal on the original prompts' structured tags, causing the model to perform much worse rather than showing the expected improvement.` cites docs/reports/marin-32b-retro.md:345-349: judge says supported. Agree? [ ]

## L03 (lookup)
Answer: In the first phase (Kestrel) of the 8B run, the data mix used was the DCLM 7B mixture in ratios roughly proportional to token count: 92.6% DCLM Baseline, 6.1% StarCoder Data, and 1.3% Proofpile 2.
- fact `DCLM Baseline 92.6%`: numbers ok, judge says stated. Agree? [ ]
- fact `StarCoder Data 6.1%`: numbers ok, judge says stated. Agree? [ ]
- fact `Proofpile 2 1.3%`: numbers ok, judge says stated. Agree? [ ]
- claim `At the beginning of the run, the DCLM 7B mix was used in ratios roughly proportional to token count.` cites docs/reports/marin-8b-retro.md:151-152: judge says supported. Agree? [ ]
- claim `The Kestrel data mix consisted of 92.6% DCLM Baseline, 6.1% StarCoder Data, and 1.3% Proofpile 2.` cites docs/reports/marin-8b-retro.md:156-160: judge says supported. Agree? [ ]

## S05 (superseded)
Answer: The final Marin 32B was produced by Phase 4b: the Mantis Cooldown (`exp1529_32b_mantis_cooldown`). It served as the second midtraining cooldown attempt after the initial Bison cooldown (`exp1529_32b_bison_cooldown`), addressing shuffling pathologies and GSM8k contamination with a Feistel-based shuffle and a cleaner math mix.
- fact `Mantis`: numbers ok, judge says stated. Agree? [ ]
- fact `the earlier Bison cooldown was abandoned after its GSM8k contamination and shuffle phase shift`: numbers ok, judge says stated. Agree? [ ]
- claim `Phase 4a was the Bison Cooldown (`exp1529_32b_bison_cooldown`) and Phase 4b was the Mantis Cooldown (`exp1529_32b_mantis_cooldown`).` cites docs/reports/marin-32b-retro.md:56-57: judge says supported. Agree? [ ]
- claim `The first midtraining attempt (Bison) exposed two issues, which the second attempt (Mantis) fixed.` cites docs/reports/marin-32b-retro.md:276-276: judge says supported. Agree? [ ]
- claim `GSM8k contamination and shuffling pathologies from a linear congruential-driven permutation were addressed in the 'Mantis' cooldown with a Feistel-based shuffle and a cleaner math mix.` cites docs/reports/marin-32b-retro.md:33-33: judge says supported. Agree? [ ]
- claim `Attempt 2 — Mantis Cooldown restarted from the 160k checkpoint with a Feistel shuffle and cleaner math mix.` cites docs/reports/marin-32b-retro.md:371-379: judge says supported. Agree? [ ]

## S06 (superseded)
Answer: As recorded on September 14, 2026, the initial mixture is in use, and phases 2 and 3 are planned in PR #9162; the log does not record them as deployed. Phase 2 (Main mixture) is planned for step 108,000 (~27.7%).
- fact `no: as recorded on September 14, 2026, the initial mixture is in use`: numbers ok, judge says NOT stated. Agree? [ ]
- fact `phases 2 and 3 are planned in PR #9162`: numbers ok, judge says stated. Agree? [ ]
- claim `As recorded on September 14, 2026, the initial mixture is in use.` cites docs/reports/hero-mixture-log.md:7-7: judge says supported. Agree? [ ]
- claim `Phases 2 and 3 are planned in PR #9162; this log does not record them as deployed.` cites docs/reports/hero-mixture-log.md:7-9: judge says supported. Agree? [ ]
- claim `Phase 2 (Main mixture) is planned for step 108,000 (~27.7%).` cites docs/reports/hero-mixture-log.md:20-20: judge says supported. Agree? [ ]

## S07 (superseded)
Answer: No, the grugformer-vs-hackable-125m experiment is not current. Its status is deleted, its purpose was a historical head-to-head comparison, and it was superseded by 8d752a775 (a template-first workflow centered on experiments/grug/base/).
- fact `no, it is deleted`: numbers ok, judge says stated. Agree? [ ]
- fact `superseded by 8d752a775, the template-first workflow centred on experiments/grug/base/`: numbers ok, judge says stated. Agree? [ ]
- claim `The status of the grugformer-vs-hackable-125m experiment is deleted.` cites docs/reports/grug-archive.md:72-76: judge says supported. Agree? [ ]
- claim `The purpose of grugformer-vs-hackable-125m was a historical head-to-head comparison.` cites docs/reports/grug-archive.md:72-77: judge says supported. Agree? [ ]
- claim `The grugformer-vs-hackable-125m experiment was superseded by 8d752a775 — template-first workflow centered on experiments/grug/base/.` cites docs/reports/grug-archive.md:72-78: judge says supported. Agree? [ ]

## T02 (table)
Answer: In the 32B Mantis cooldown mixture table, 6 datasets have a share above 5%: `nemotron_cc/medium` (21.49%), `nemotron_cc/hq_synth` (17.29%), `nemotron_cc/medium_low` (9.79%), `nemotron_cc/hq_actual` (5.81%), `megamath/web` (5.57%), and `nemotron_cc/medium_high` (5.24%).
- fact `6`: numbers ok, judge says stated. Agree? [ ]
- claim `There are 6 datasets in the Mantis cooldown mixture with a percentage share above 5%.` cites docs/reports/marin-32b-retro.md:383-407: judge says supported. Agree? [ ]
- claim `In the 32B Mantis cooldown mixture, nemotron_cc/medium has a share of 21.49%, nemotron_cc/hq_synth has 17.29%, nemotron_cc/medium_low has 9.79%, nemotron_cc/hq_actual has 5.81%, nemotron_cc/medium_high has 5.24%, and megamath/web has 5.57%.` cites docs/reports/marin-32b-retro.md:385-392: judge says supported. Agree? [ ]

## W05 (why)
Answer: The 32B run switched to the Qwen3 32B backbone because the team concluded that stabilizing a 32B Llama without architectural help was not feasible under their constraints after encountering a loss-instability episode around 70k–80k steps. The Qwen3 32B backbone adds QK-Norm in attention, which resolved the instability and stabilized training.
- fact `at 80k steps spikes were unavoidable even with update clipping`: numbers ok, judge says NOT stated. Agree? [ ]
- fact `QK-Norm`: numbers ok, judge says stated. Agree? [ ]
- fact `warm-started from the 80k Llama weights`: numbers ok, judge says NOT stated. Agree? [ ]
- claim `The team concluded that stabilizing a 32B Llama without architectural help wasn't feasible under their constraints.` cites docs/reports/marin-32b-retro.md:247-247: judge says supported. Agree? [ ]
- claim `A loss-instability episode occurred around 70k–80k steps in exp1295_32b that was ultimately resolved by introducing QK-Norm via a switch to the Qwen3 32B backbone.` cites docs/reports/marin-32b-retro.md:32-32: judge says supported. Agree? [ ]
- claim `The switch to Qwen3 32B adds QK-Norm in attention.` cites docs/reports/marin-32b-retro.md:247-247: judge says supported. Agree? [ ]
- claim `Switching to Qwen3 32B (QK-Norm) stabilized the loss and allowed training to recover.` cites docs/reports/marin-32b-retro.md:45-45: judge says supported. Agree? [ ]
