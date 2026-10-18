# Gold-range candidates: marin

Proposed by plain text search (researchledger/gold.py). Nothing here changes the evaluation set.

## L01 (lookup): What architecture settings did Marin 8B use?
Facts: [1] the same settings as Llama 3.1 8B; [2] hidden_dim 4096; [3] 32 layers; [4] 8 KV heads
Current gold: docs/reports/marin-8b-retro.md:62-71
- `docs/reports/agent-moe-experiments.md:60-60` matches facts [4]: | [#5047 Wide attention](https://github.com/marin-community/marin/issues/5047) | More attention heads increase attention capacity without shrinking head dimension. | Worked | ≈1.10–1.16x | 1.04–1.07x | More heads consist
- `docs/reports/marin-32b-retro.md:86-86` matches facts [4]: | `num_kv_heads` | 8 |
- `docs/reports/marin-32b-retro.md:102-102` matches facts [4]: | `num_kv_heads` | 8 |
- `docs/reports/marin-8b-retro.md:77-79` matches facts [3]: We used mixed float32/bfloat16 precision, with parameters and optimizer states in float32 and compute in bfloat16 (except for the final softmax over the vocabulary.) We used the [AdamW](https://arxiv.org/abs/1711.05101) 
- `docs/reports/marin-8b-retro.md:356-356` matches facts [1]: A 5-shot MMLU of 65.3 was better than both Olmo 2 7B (63.9) and DCLM (64.4), and not too far behind Llama 3.1 8B (66.4).[^MMLU scores] But we can do better.
- `docs/reports/marin-8b-retro.md:423-424` matches facts [1]: The genesis of Raccoon was that we were having trouble getting our model to perform well after supervised fine tuning (SFT). While our nascent SFT pipeline would exhibit an "epoch cliff" (i.e. loss would jump down on eac
- ... 1 more weaker matches not shown

## L02 (lookup): Which tokenizer does Marin use, and why?
Facts: [1] Llama 3 tokenizer; [2] outperformed Llama 2 and NeoX in bits-per-byte
Current gold: docs/reports/marin-8b-retro.md:83-83
- `docs/reports/index.md:65-86` matches facts [1, 2]: - Pick Tokenizer type [![#524](https://img.shields.io/github/issues/detail/state/marin-community/marin/524)](https://github.com/marin-community/marin/issues/524) - [GitHub Issue #524](https://github.com/marin-community/m
- `docs/reports/agent-moe-experiments.md:59-59` matches facts [1]: | [#4986 Value embeddings](https://github.com/marin-community/marin/issues/4986) | Token-indexed values inject lexical information directly into attention retrieval. | Did not work | Mixed | <1x | One initialization was 
- `docs/reports/index.md:172-185` matches facts [1]: - Reproduce olmov2 SFT [![#606](https://img.shields.io/github/issues/detail/state/marin-community/marin/606)](https://github.com/marin-community/marin/issues/606) - [GitHub Issue #606](https://github.com/marin-community/
- `docs/reports/marin-32b-retro.md:75-76` matches facts [1]: - Initial backbone: Llama 32B (Llama‑3–style settings) - Gradient checkpointing: offload carries to fit large global batches on a v4‑2048 slice
- `docs/reports/marin-32b-retro.md:78-78` matches facts [1]: #### Llama-3-style 32B (Phase 1–2) parameters
- `docs/reports/marin-32b-retro.md:236-236` matches facts [1]: **Tokens trained:** Diagnostic restarts only (short runs of a few thousand steps); excluded from cumulative phase totals due to restart to 80k Llama checkpoint for Phase 3.
- ... 23 more weaker matches not shown

## L03 (lookup): What was the data mix in the first phase (Kestrel) of the 8B run?
Facts: [1] DCLM Baseline 92.6%; [2] StarCoder Data 6.1%; [3] Proofpile 2 1.3%
Current gold: docs/reports/marin-8b-retro.md:151-160
Candidates: none

## L04 (lookup): What peak learning rate and weight decay did the 8B Kestrel phase use?
Facts: [1] 1e-3; [2] roughly 3x Olmo 2 7B's 3e-4; [3] weight decay 0.05
Current gold: docs/reports/marin-8b-retro.md:189-192
- `docs/reports/marin-32b-retro.md:118-118` matches facts [3]: | Weight decay | 0.05 |
- `docs/reports/marin-8b-retro.md:194-195` matches facts [1]: We initially opted to not use Z-loss because we didn't have problems with LR=1e-3 and wanted to keep things as simple as possible. In retrospect, we should have used it and have since made it the default for future Marin

## L05 (lookup): What did the 8B model score on MMLU 5-shot and GSM8K after the first cooldown (Jellyfish)?
Facts: [1] MMLU 5-shot 65.3; [2] GSM8K 50.9
Current gold: docs/reports/marin-8b-retro.md:347-356
Candidates: none

## L06 (lookup): What hardware did the 32B run use?
Facts: [1] 4 preemptible TPU v5p-512 slices; [2] 3 slices at 18,500 steps; [3] reserved v4-2048 from 21,010 steps
Current gold: docs/reports/marin-32b-retro.md:69-71
- `docs/reports/marin-32b-retro.md:159-161` matches facts [1]: The change in global batch size was driven by changing hardware: when we had the 4 v5p-512s we used 8192, shifting down to 7680 for divisibility by 3 when we had 3 v5p-512s, and finally changing back to 8192 when we move

## L07 (lookup): How many tokens went into the final Marin 32B artifact?
Facts: [1] 6.437T; [2] 2.679T + 2.684T + 1.074T; [3] excludes diagnostic restarts and the abandoned Bison cooldown
Current gold: docs/reports/marin-32b-retro.md:59-63
- `docs/reports/marin-32b-retro.md:5-20` matches facts [3]: - [Introduction](#introduction) - [Baseline Configuration](#baseline-configuration) - [Architecture](#architecture) - [Optimizer & Schedule](#optimizer--schedule) - [Data Mix & Batch Schedule](#data-mix--batch-schedule) 
- `docs/reports/marin-32b-retro.md:52-57` matches facts [3]: - Phase 1 \- Baseline: [#1295](https://github.com/marin-community/marin/issues/1295) [`exp1295_32b`](https://github.com/marin-community/marin/blob/5e88b5253975ffd13e63a5db0b946883c8660e1b/experiments/tootsie/exp1295_32b.
- `docs/reports/marin-32b-retro.md:236-236` matches facts [3]: **Tokens trained:** Diagnostic restarts only (short runs of a few thousand steps); excluded from cumulative phase totals due to restart to 80k Llama checkpoint for Phase 3.
- `docs/reports/marin-32b-retro.md:513-517` matches facts [3]: - **Pride goeth before a fall.** Our initial hubris in thinking we could scale our recipe to 32B without QK‑Norm cost us time and compute. We should have tested QK‑Norm earlier. - **Midflight changes can work.** The Toot

## L08 (lookup): What optimizer and learning-rate schedule did the 32B baseline use?
Facts: [1] AdamW; [2] peak LR 7e-4; [3] warmup 1% of steps; [4] decay 40% of steps
Current gold: docs/reports/marin-32b-retro.md:109-117
- `docs/reports/hero-mixture-log.md:3-5` matches facts [4]: This records the hero's mixture in training order. All entries use `store_4d2e363d`: 40 topic clusters × five quality buckets. Steps count completed training updates; a mixture listed at step N applies after N updates ha
- `docs/reports/marin-32b-retro.md:119-119` matches facts [3]: | Max grad norm | initially 1.0, then 0.2 from 56.4K steps |
- `docs/reports/marin-32b-retro.md:186-189` matches facts [3]: #### 1. Tightened max grad norm clipping Following standard practice, by default we have clipped our grad norm to a maximum of 1.0. We observed that loss spikes typically occurred after steps with a large grad norm, but 
- `docs/reports/marin-32b-retro.md:369-369` matches facts [3]: **Tokens trained:** ≈1.074T tokens (32,000 steps from 160k → 192k at 4096 seq len, global batch 8192).
- `docs/reports/marin-32b-retro.md:415-415` matches facts [3]: **Tokens trained:** ≈1.074T tokens (32,000 steps from 160k → 192k at 4096 seq len, global batch 8192).
- `docs/reports/marin-8b-retro.md:178-181` matches facts [3]: For the first 200K steps, we did a decay cycle every 10k steps for 1k steps. However, I (@dlwh) got worried that we weren't seeing significant improvement in evaluation losses. We then moved to a decay cycle every 20k st
- ... 7 more weaker matches not shown

## L09 (lookup): How does Marin 32B (Mantis) compare with OLMo 2 32B Base on average accuracy?
Facts: [1] 65.2 vs 63.2; [2] +2.0; [3] better on 14 of 19 tasks
Current gold: docs/reports/marin-32b-retro.md:445-449, docs/reports/marin-32b-retro.md:471-471
- `docs/reports/agent-moe-experiments.md:114-114` matches facts [2]: | [#8131 Factorized row-norm linears](https://github.com/marin-community/marin/issues/8131) | Separating output scale from direction could improve conditioning under norm-preserving updates. | Did not work | 0.915x | 0.8
- `docs/reports/marin-32b-retro.md:120-120` matches facts [2]: | Clip update norm | on (σ=2.0, rolling=128); added at 72233, briefly off ~74k–80k |
- `docs/reports/marin-32b-retro.md:123-123` matches facts [2]: | Skip bad steps | true (σ=2.0, rolling=128) |

## L10 (lookup): What Paloma c4_en bits-per-byte did the first daily ferry run reach, and when did it run?
Facts: [1] 1.12509; [2] 2026-02-20 (completed 2026-02-21); [3] 125M
Current gold: docs/experiments/daily-ferry-log.md:16-24
- `docs/reports/grug-archive.md:72-78` matches facts [3]: ### grugformer-vs-hackable-125m - Path: `experiments/speedrun/grugformer_vs_hackable_125m/grugformer_vs_hackable_125m.py` - Introduced: 5efe76834 - Last known-good: 5efe76834 - Status: deleted - Purpose: historical head-
- `docs/reports/markdownified-datasets.md:16-16` matches facts [3]: These datasets were processed using our [custom fork of Resiliparse](https://github.com/stanford-crfm/chatnoir-resiliparse) which simplified the raw HTML DOM, the simplified DOM was then processed by our [custom implemen

## L11 (lookup): Which data store does the hero mixture log use, and how is it organised?
Facts: [1] store_4d2e363d; [2] 40 topic clusters; [3] five quality buckets
Current gold: docs/reports/hero-mixture-log.md:3-5
- `docs/reports/hero-mixture-log.md:32-35` matches facts [3]: Increase natural-science research from 6.9% in phase 2 to 11.3%. Low-level code and agent transcripts retain large shares; general software development and math fall further. The highest classifier-rated quality bucket, 
- `docs/reports/hero-mixture-log.md:43-45` matches facts [3]: Shares sum each topic's configured weights across its five quality buckets. They describe sampling weights, not measured token counts. Labels summarize clusters' dominant content; a cluster can contain other topics.
- `docs/reports/hero-mixture-log.md:60-61` matches facts [2]: See the [cluster labels and examples](https://storage.googleapis.com/marin-public/held/harrier-k40-cluster-overview/2026.08.18/index.html?revision=uniform-sampling) and [all topic and quality shares](https://storage.goog

## L12 (lookup): What z-loss penalty was added in the Spoonbill cooldown?
Facts: [1] 1e-4 on the final logits
Current gold: docs/reports/marin-8b-retro.md:459-459
- `docs/reports/marin-8b-retro.md:550-551` matches facts [1]: Based on our findings in the "Raccoon" and "Spoonbill" deep cooldowns (where we observed steady loss increases at low learning rate), we imposed a z-loss penalty of 1e-4 on the final logits.

## W01 (why): Why was Marin 8B built at roughly 7-8 billion parameters?
Facts: [1] reserved capacity only allowed a model of that size to be trained long enough
Current gold: docs/reports/marin-8b-retro.md:54-55
Candidates: none

## W02 (why): Why was the WSD-S decay cycle changed at step 200k?
Facts: [1] no significant improvement in eval losses; [2] hypothesis that longer cooldowns would show more progress; [3] decay every 20k steps for 2k steps instead of every 10k for 1k
Current gold: docs/reports/marin-8b-retro.md:178-180, docs/reports/marin-8b-retro.md:209-212
- `docs/reports/marin-32b-retro.md:345-348` matches facts [1]: Dolmino’s GSM8k uses OLMes formatting, not LM Eval’s default. Therefore, rather than the expected improvement in results from training on the test, contamination made our model have dramatically increased surprisal on th
- `docs/reports/marin-32b-retro.md:361-363` matches facts [1]: As you can see, this "spike" ended up being a phase shift in training loss that never recovered. But, eval losses were unaffected. This strongly indicated that the underlying data had shifted, rather than any model insta
- `docs/reports/marin-32b-retro.md:434-434` matches facts [1]: ![Overall Paloma average losses improve under Mantis cooldown relative to Bison](32b-paloma-average-permutation.png)
- `docs/reports/marin-8b-retro.md:218-220` matches facts [1]: As expected, this led to a drop in eval losses that most looked like our training data. In the below, the orange line is eval loss (Paloma's c4en), while the blue line is training loss. There is a noticeable drop in both
- `docs/reports/marin-8b-retro.md:224-229` matches facts [1]: Interestingly, not all eval losses dropped. In fact, for some domains, the eval loss increased. We saw decreases in `mc4`, `c4en`, `m2d2 wikipedia`, `m2d2 s2orc`, and `refined web`, but marked increases in `100_subreddit
- `docs/reports/marin-8b-retro.md:231-231` matches facts [1]: ![graph depicting many eval losses after the transition to longer decay phases](../images/tootsie-8b-wsd-s-losses-post-transition.png)
- ... 2 more weaker matches not shown

## W03 (why): Why did some Paloma eval losses rise after the switch to longer decay phases?
Facts: [1] some Paloma domains' texts end with a space character that was not stripped; [2] the training data was not formatted that way
Current gold: docs/reports/marin-8b-retro.md:224-228
- `docs/reports/agent-moe-experiments.md:188-188` matches facts [2]: ## Training setup, data, objective, serving, and evaluation
- `docs/reports/index.md:116-145` matches facts [2]: - Ablations on Cooldown for Markdownified Wikipedia [![#845](https://img.shields.io/github/issues/detail/state/marin-community/marin/845)](https://github.com/marin-community/marin/issues/845) - [GitHub Issue #845](https:
- `docs/reports/index.md:159-168` matches facts [2]: - Compare HTML -> text methods [![#246](https://img.shields.io/github/issues/detail/state/marin-community/marin/246)](https://github.com/marin-community/marin/issues/246) - [GitHub Issue #246](https://github.com/marin-co
- `docs/reports/marin-32b-retro.md:5-20` matches facts [2]: - [Introduction](#introduction) - [Baseline Configuration](#baseline-configuration) - [Architecture](#architecture) - [Optimizer & Schedule](#optimizer--schedule) - [Data Mix & Batch Schedule](#data-mix--batch-schedule) 
- `docs/reports/marin-32b-retro.md:275-276` matches facts [2]: With stability restored, we trained until we completed 1 epoch over the Nemotron data and then resumed the 8B playbook. The first attempt (*Bison*) mirrored our [Starling](./marin-8b-retro.md#phase-5-starling-second-cool
- `docs/reports/marin-32b-retro.md:345-348` matches facts [2]: Dolmino’s GSM8k uses OLMes formatting, not LM Eval’s default. Therefore, rather than the expected improvement in results from training on the test, contamination made our model have dramatically increased surprisal on th
- ... 21 more weaker matches not shown

## W04 (why): Why was FLAN mixed into the microannealing runs?
Facts: [1] high-quality data lacks few-shot-inducing data such as multiple-choice questions; [2] 70% PT / 15% FLAN / 15% HQ gave the best results
Current gold: docs/reports/marin-8b-retro.md:283-290
- `docs/reports/marin-8b-retro.md:296-301` matches facts [1, 2]: - Naively oversampling "high-quality" (HQ) sources improved loss on HQ eval sets, but degraded general task performance. - HQ data often lacks formats useful for few-shot learning (e.g., multiple-choice Q&A). - Mixing in
- `docs/reports/marin-8b-retro.md:526-526` matches facts [1]: [Marin Datashop Science QA](https://huggingface.co/datasets/marin-community/datashop-science-qa) is a new dataset of 12.6B mostly science questions generated by rephrasing science-related web content using Marin Datashop

## W05 (why): Why did the 32B run switch to the Qwen3 backbone?
Facts: [1] at 80k steps spikes were unavoidable even with update clipping; [2] QK-Norm; [3] warm-started from the 80k Llama weights
Current gold: docs/reports/marin-32b-retro.md:208-208, docs/reports/marin-32b-retro.md:247-247
- `docs/reports/marin-32b-retro.md:191-192` matches facts [1]: #### 2. Clip Update Norm When that didn't work, we added a "clip update norm" filter at around 72.2K steps. Like grad norm spikes, update norm spikes always preceded grad norm spikes, and we thought these would be a more

## W06 (why): Why did the 32B model do so badly on GSM8k after the Bison cooldown?
Facts: [1] contamination: the Dolmino math bundle included GSM8k test items in test.json, already cached on the cluster; [2] OLMes formatting made the LM Eval prompts' tags more surprising; [3] about 22 points worse than the weakest baseline
Current gold: docs/reports/marin-32b-retro.md:337-348
- `docs/reports/marin-32b-retro.md:442-443` matches facts [2]: We evaluate with Eleuther's [LM Eval Harness](https://github.com/EleutherAI/lm-evaluation-harness) defaults across a standard suite. Numbers may differ from model cards or other evaluation harnesses (e.g. OLMES) due to p

## W07 (why): Why did the training loss phase-shift near step 190k in the Bison cooldown?
Facts: [1] the co-prime step-size (linear) shuffle produced batches from correlated data; [2] eval losses were unaffected, so the data shifted rather than the model becoming unstable
Current gold: docs/reports/marin-32b-retro.md:355-363
Candidates: none

## W08 (why): Why didn't the 32B run use QK-Norm from the start?
Facts: [1] the 8B run had been stable without QK-Norm; [2] an earlier 70B trial was also stable without it
Current gold: docs/reports/marin-32b-retro.md:250-250
- `docs/reports/marin-32b-retro.md:513-517` matches facts [1]: - **Pride goeth before a fall.** Our initial hubris in thinking we could scale our recipe to 32B without QK‑Norm cost us time and compute. We should have tested QK‑Norm earlier. - **Midflight changes can work.** The Toot

## S01 (superseded): What batch size did the 8B run train with?
Facts: [1] 16Mi tokens in the final Starling cooldown; [2] 12Mi from about 2.77e12 tokens (Ocelot); [3] 4Mi at the start (Kestrel)
Current gold: docs/reports/marin-8b-retro.md:87-87, docs/reports/marin-8b-retro.md:242-242, docs/reports/marin-8b-retro.md:478-478
- `docs/reports/marin-32b-retro.md:69-71` matches facts [3]: We initially started the 32B run on 4 preemptible TPU v5p-512 slices coordinated with multislice, moving to 3 slices at 18,500 steps as spare capacity dried up, and eventually moving to a reserved v4-2048 once the preemp
- `docs/reports/marin-8b-retro.md:8-23` matches facts [3]: - [Introduction](#introduction) - [The "Tootsie Roll" process](#the-tootsie-roll-process) - [Model Basics](#model-basics) - [Training Phases](#training-phases) - [Phase 1: Kestrel (DCLM WSD-S Phase)](#phase-1-kestrel-dcl
- `docs/reports/marin-8b-retro.md:112-116` matches facts [3]: - *Kestrel (DCLM WSD-S Phase)*: In the first phase, we used the "DCLM mix" and [WSD-S](https://arxiv.org/abs/2410.05192) for about 2.7T tokens. We used 2x TPU v5e-256 coordinated with multislice for this. (0→2.7T tokens)
- `docs/reports/marin-8b-retro.md:426-428` matches facts [3]: Starting from the jellyfish cooldown, we further cooled down the model from 1.7e-4 to 1.7e-5 over about 100B tokens. ([WandB report here](https://wandb.ai/stanford-mercury/marin/reports/898-Tootsie-Soft-Raccoon--Vmlldzox
- `docs/reports/marin-8b-retro.md:465-467` matches facts [3]: Interestingly, [subsequent experiments](https://wandb.ai/marin-community/marin/reports/ZLoss-vs-Not-1-4B--VmlldzoxMjEzMzA1NA) showed that, when starting from scratch, z-loss **increases** the norm of the lm_head, while i
- `docs/reports/marin-8b-retro.md:621-622` matches facts [3]: We used a batch size of 512Ki tokens and a learning rate of 1.7e-4. We started from the final checkpoint of the Deeper Starling run. We train for about 5Gi tokens, 10,227 steps.

## S02 (superseded): What data shuffle does Marin use?
Facts: [1] a Feistel-network permutation since the Mantis cooldown; [2] replaced the affine/LCG permutation p(x) = (a * x + b) % N
Current gold: docs/reports/marin-32b-retro.md:422-426
- `docs/reports/marin-32b-retro.md:30-33` matches facts [1]: We deliberately reused the [Nemotron-CC](https://arxiv.org/abs/2412.02595)-centric pretraining mixture and the AdamW-based schedule that behaved well at 8B. That mostly transferred. The notable exception was a loss-insta
- `docs/reports/marin-32b-retro.md:46-46` matches facts [1]: | 4 | 160,000 → 192,000 | 1.074 | Mantis cooldown (Feistel shuffle, better math mix) | Strong results; resolved anomalies from Bison |
- `docs/reports/marin-32b-retro.md:378-379` matches facts [2]: - Feistel shuffle. Switched from linear permutation to a more robust Feistel‑based shuffle. - Cleaner math mix. Replaced Dolmino math with [MegaMath](https://arxiv.org/abs/2504.02807) splits and later added [Common Pile]
- `docs/reports/marin-32b-retro.md:428-428` matches facts [1]: ![Feistel shuffle removes the cooldown phase shift versus the prior linear permutation](32b-feistel-vs-lcg.png)
- `docs/reports/marin-32b-retro.md:513-517` matches facts [1]: - **Pride goeth before a fall.** Our initial hubris in thinking we could scale our recipe to 32B without QK‑Norm cost us time and compute. We should have tested QK‑Norm earlier. - **Midflight changes can work.** The Toot
- `docs/reports/marin-32b-retro.md:530-536` matches facts [1]: - **AdamC** — An adjusted weight‑decay computation used during LR decay to reduce gradient growth. - **Cooldown** — A training phase with gradually decreased LR, often paired with a higher‑quality, more structured data m

## S03 (superseded): Which backbone is Marin 32B?
Facts: [1] Qwen3 32B with QK-Norm from step 80,000; [2] replaced the Llama 32B backbone used for steps 0-80,000
Current gold: docs/reports/marin-32b-retro.md:43-45, docs/reports/marin-32b-retro.md:247-247
Candidates: none

## S04 (superseded): What max grad norm did the 32B run clip to?
Facts: [1] 0.2 from 56.4K steps; [2] initially 1.0
Current gold: docs/reports/marin-32b-retro.md:119-119, docs/reports/marin-32b-retro.md:187-189
- `docs/reports/agent-moe-experiments.md:123-123` matches facts [2]: | [#5203 AdamH embedding initialization](https://github.com/marin-community/marin/issues/5203) | Unit-variance embeddings make initial RMSNorm neutral while AdamH preserves embedding norms. | Worked | ≈1.01–1.05x | 1.014

## S05 (superseded): Which cooldown produced the final Marin 32B?
Facts: [1] Mantis; [2] the earlier Bison cooldown was abandoned after its GSM8k contamination and shuffle phase shift
Current gold: docs/reports/marin-32b-retro.md:46-46, docs/reports/marin-32b-retro.md:63-63, docs/reports/marin-32b-retro.md:376-379
- `docs/reports/marin-32b-retro.md:513-517` matches facts [2]: - **Pride goeth before a fall.** Our initial hubris in thinking we could scale our recipe to 32B without QK‑Norm cost us time and compute. We should have tested QK‑Norm earlier. - **Midflight changes can work.** The Toot

## S06 (superseded): Has phase 2 of the hero mixture been deployed?
Facts: [1] no: as recorded on September 14, 2026, the initial mixture is in use; [2] phases 2 and 3 are planned in PR #9162
Current gold: docs/reports/hero-mixture-log.md:7-9
Candidates: none

## S07 (superseded): Is the grugformer-vs-hackable-125m experiment still current?
Facts: [1] no, it is deleted; [2] superseded by 8d752a775, the template-first workflow centred on experiments/grug/base/
Current gold: docs/reports/grug-archive.md:72-78
- `docs/reports/grug-archive.md:31-36` matches facts [2]: ### grug-base-template - Path: `experiments/grug/base/` - Origin: base - Introduced: 8d752a775 - Status: active - Purpose: canonical grug template (model/train/launch).

## S08 (superseded): What rotary embedding settings did Marin 8B use?
Facts: [1] Llama 3-style from the Ocelot phase; [2] Llama 2's settings before that, by mistake
Current gold: docs/reports/marin-8b-retro.md:251-251
- `docs/reports/marin-32b-retro.md:75-76` matches facts [1]: - Initial backbone: Llama 32B (Llama‑3–style settings) - Gradient checkpointing: offload carries to fit large global batches on a v4‑2048 slice
- `docs/reports/marin-32b-retro.md:78-78` matches facts [1]: #### Llama-3-style 32B (Phase 1–2) parameters
- `docs/reports/marin-32b-retro.md:92-92` matches facts [1]: #### Qwen3-style 32B (Phase 3+) parameters
- `docs/reports/marin-32b-retro.md:236-236` matches facts [1]: **Tokens trained:** Diagnostic restarts only (short runs of a few thousand steps); excluded from cumulative phase totals due to restart to 80k Llama checkpoint for Phase 3.
- `docs/reports/marin-8b-retro.md:8-23` matches facts [1]: - [Introduction](#introduction) - [The "Tootsie Roll" process](#the-tootsie-roll-process) - [Model Basics](#model-basics) - [Training Phases](#training-phases) - [Phase 1: Kestrel (DCLM WSD-S Phase)](#phase-1-kestrel-dcl
- `docs/reports/marin-8b-retro.md:112-116` matches facts [1]: - *Kestrel (DCLM WSD-S Phase)*: In the first phase, we used the "DCLM mix" and [WSD-S](https://arxiv.org/abs/2410.05192) for about 2.7T tokens. We used 2x TPU v5e-256 coordinated with multislice for this. (0→2.7T tokens)

## C01 (claim): Check: 'Marin 8B Base beats Llama 3.1 Base on every benchmark'
Facts: [1] higher average, 66.6 vs 65.3, and better on most tasks; [2] lower on GPQA (30.3 vs 32.3)
Current gold: docs/reports/marin-8b-retro.md:588-591, docs/reports/marin-8b-retro.md:596-596
Candidates: none

## C02 (claim): Check: 'a z-loss penalty fixed the training loss creeping up during Marin 8B's deep cooldowns'
Facts: [1] the lm_head was exploding; [2] z-loss penalty of 1e-4 on the final logits
Current gold: docs/reports/marin-8b-retro.md:455-461
- `docs/reports/marin-32b-retro.md:530-536` matches facts [1]: - **AdamC** — An adjusted weight‑decay computation used during LR decay to reduce gradient growth. - **Cooldown** — A training phase with gradually decreased LR, often paired with a higher‑quality, more structured data m
- `docs/reports/marin-8b-retro.md:476-478` matches facts [2]: - We deepened the cooldown to 1.7e-5, rather than 1.7e-4. - We added a small z-loss penalty of 1e-4. - We increased the batch size to 16Mi tokens rather than 12Mi.
- `docs/reports/marin-8b-retro.md:550-551` matches facts [2]: Based on our findings in the "Raccoon" and "Spoonbill" deep cooldowns (where we observed steady loss increases at low learning rate), we imposed a z-loss penalty of 1e-4 on the final logits.

## C03 (claim): Check: 'switching the 32B run to the Muon optimizer fixed its loss spikes'
Facts: [1] the Muon run turned into gradient ascent and was abandoned
Current gold: docs/reports/marin-32b-retro.md:231-231
Candidates: none

## C04 (claim): Check: 'Marin 32B (Mantis) is the best open-weights base model in its comparison'
Facts: [1] best mean rank, 3.05; [2] Qwen 2.5 32B Base has a higher mean reciprocal rank (0.54 vs 0.44)
Current gold: docs/reports/marin-32b-retro.md:459-469
Candidates: none

## C05 (claim): Check: 'in the Ocelot phase the 8B batch size was increased by 50%'
Facts: [1] the record conflicts: the phase summary says 50%, the Ocelot section says 3x, to 12Mi tokens, from 4Mi
Current gold: docs/reports/marin-8b-retro.md:113-113, docs/reports/marin-8b-retro.md:187-187, docs/reports/marin-8b-retro.md:242-242
Candidates: none

## C06 (claim): Check: 'GSM8k contamination inflated Marin 32B's GSM8K score'
Facts: [1] the contamination made it worse: about 22 points below the weakest baseline
Current gold: docs/reports/marin-32b-retro.md:337-348
Candidates: none

## C07 (claim): Check: 'adding FLAN in the 8B dessert runs improved MMLU'
Facts: [1] MMLU 5-shot .653 -> .651; [2] the math datasets improved GSM8K from 0.509 to 0.611
Current gold: docs/reports/marin-8b-retro.md:380-381
Candidates: none

## T01 (table): Which datasets in the 8B Starling cooldown mix were oversampled 10x?
Facts: [1] Dolmino FLAN; [2] Dolmino Math
Current gold: docs/reports/marin-8b-retro.md:490-510
- `docs/reports/marin-32b-retro.md:312-313` matches facts [1, 2]: Within the 70/30 split, each data source was weighted approximately equal to its token size, but we upsampled FLAN (10x) and the math from Dolmino (2x). Again, this is the same as the starling cooldown at 8B.
- `docs/reports/marin-8b-retro.md:334-337` matches facts [1, 2]: - We included datasets that [Olmo 2](https://arxiv.org/abs/2501.00656) used in its Phase 1 (e.g. wikipedia) that we did not. - We did not include [FLAN](https://arxiv.org/abs/2109.01652). (We were suspicious of its fairl
- `docs/reports/marin-8b-retro.md:375-378` matches facts [1, 2]: While our "mainline" run continued in the Phoenix phase, we ran a number of short ablations consisting of what we termed "dessert" runs. Dessert coasted at the same already-low, learning rate with the goal of patching a 
- `docs/reports/marin-32b-retro.md:30-33` matches facts [2]: We deliberately reused the [Nemotron-CC](https://arxiv.org/abs/2412.02595)-centric pretraining mixture and the AdamW-based schedule that behaved well at 8B. That mostly transferred. The notable exception was a loss-insta
- `docs/reports/marin-32b-retro.md:302-302` matches facts [1]: | dolmino/flan | 4.33% |
- `docs/reports/marin-32b-retro.md:341-343` matches facts [2]: We determined the root cause to be contamination. That is, we (accidentally) cheated but we cheated badly. Our [Dolmino](https://huggingface.co/datasets/allenai/dolmino-mix-1124/tree/main/data/math) math bundle included 
- ... 5 more weaker matches not shown

## T02 (table): How many datasets in the 32B Mantis cooldown mixture have a share above 5%?
Facts: [1] 6
Current gold: docs/reports/marin-32b-retro.md:383-407
- `docs/reports/agent-moe-experiments.md:35-35` matches facts [1]: | Not evaluated | 6 | No usable comparison was recorded, often because the work was superseded. |
- `docs/reports/agent-moe-experiments.md:113-113` matches facts [1]: | [#6388 MuonH magnitude-direction decoupling](https://github.com/marin-community/marin/issues/6388) | Separating normalized directions from learned gains could improve conditioning and LR transfer. | In progress | >1x |
- `docs/reports/agent-moe-experiments.md:211-214` matches facts [1]: - [#5184 AdamH on token embeddings](https://github.com/marin-community/marin/issues/5184) Moved token embeddings to AdamH and feeds the May architecture. - [#5292 k6e256s5 expert configuration](https://github.com/marin-c
- `docs/reports/hero-mixture-log.md:17-18` matches facts [1]: Weights: `phases[0].weights` (`initial`) in [`harrier_mix_2026_08_18.json`](https://github.com/marin-community/marin/blob/7c996f66bfa7baf7bf81cb5c6d62cc8b8dc720fb/experiments/grug/moe_hero_ep/harrier_mix_2026_08_18.json)
- `docs/reports/hero-mixture-log.md:26-28` matches facts [1]: Weights: `phases[1].weights` (`main`) in [`harrier_mix_2026_08_18.json`](https://github.com/marin-community/marin/blob/7c996f66bfa7baf7bf81cb5c6d62cc8b8dc720fb/experiments/grug/moe_hero_ep/harrier_mix_2026_08_18.json). T
- `docs/reports/hero-mixture-log.md:32-35` matches facts [1]: Increase natural-science research from 6.9% in phase 2 to 11.3%. Low-level code and agent transcripts retain large shares; general software development and math fall further. The highest classifier-rated quality bucket, 
- ... 17 more weaker matches not shown

## T03 (table): On how many of the 19 base-model tasks does Marin 32B (Mantis) score higher than Marin 32B (Bison)?
Facts: [1] 13
Current gold: docs/reports/marin-32b-retro.md:445-448
- `docs/reports/agent-moe-experiments.md:33-33` matches facts [1]: | Mixed | 13 | The answer changed by scale or metric, or a strict projection failed. |
- `docs/reports/agent-moe-experiments.md:53-53` matches facts [1]: | [#7208 Inkling relative position](https://github.com/marin-community/marin/issues/7208) | Learned query-dependent relative bias can model positional relationships more flexibly. | Did not work | <1x | <1x | The correct
- `docs/reports/index.md:50-61` matches facts [1]: - \[EPIC\] Big Runs [![#859](https://img.shields.io/github/issues/detail/state/marin-community/marin/859)](https://github.com/marin-community/marin/issues/859) - [GitHub Issue #859](https://github.com/marin-community/mar
- `docs/reports/marin-32b-retro.md:52-57` matches facts [1]: - Phase 1 \- Baseline: [#1295](https://github.com/marin-community/marin/issues/1295) [`exp1295_32b`](https://github.com/marin-community/marin/blob/5e88b5253975ffd13e63a5db0b946883c8660e1b/experiments/tootsie/exp1295_32b.
- `docs/reports/marin-32b-retro.md:143-143` matches facts [1]: | nemotron_cc/medium_low | 13.98% |
- `docs/reports/marin-32b-retro.md:169-170` matches facts [1]: - Issue: [#1295](https://github.com/marin-community/marin/issues/1295) - Experiment: [`exp1295_32b`](https://github.com/marin-community/marin/blob/5e88b5253975ffd13e63a5db0b946883c8660e1b/experiments/tootsie/exp1295_32b.
