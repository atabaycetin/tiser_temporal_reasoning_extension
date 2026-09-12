# Tennis Domain Adaptation: Current Status and Next Steps

This document separates claims supported by committed artifacts from missing
provenance and future experiments. It is the source of truth for the tennis
extension; older condition names in result metadata are retained as historical
identifiers.

The semantic, trace, and reflection audits are complete. Tennis semantics and
training traces use separate GPT-5.6 Sol audits under
`results/tennis_semantic_audit_v2` and `results/tennis_trace_audit_v2`. The
completed conditional GPU workflow is recorded by
`notebooks/colab_conditional_retention.ipynb` and
`results/forgetting_replay/study_v2`.

## Dataset State

The following counts are directly verifiable from the tracked files:

| Artifact | Records | Role |
| --- | ---: | --- |
| `data/tennis/raw/tennis_raw.json` | 1,122 | Raw context/question/answer records |
| `data/tennis/processed/tennis_all_tiser.json` | 1,122 | Converted TISER-style records |
| `data/tennis/tennis_train.json` | 785 | Train split |
| `data/tennis/tennis_dev.json` | 113 | Development split |
| `data/tennis/tennis_test.json` | 224 | Test split |
| `data/tennis/tennis_train_traced_full.json` | 600 | Generated and validated training traces |

The raw-data audit is reproducible. Conversion with
`--deterministic-output --prompt-version reported`, followed by the seeded split
command, byte-reproduces the tracked converted records and train/dev/test files.
The default `strict` prompt mode is intentionally separate and should be used
only for newly labelled experiments.

ChatGPT-5.5 created the raw examples using the prompt in
`RAW_GENERATION_PROMPT.md`. It then generated supervised TISER traces from
training examples and their supplied gold answers using the prompt in
`TRACE_GENERATION_PROMPT.md`. The historical `source: unknown` fields remain
unchanged for byte reproducibility. The dataset card and machine-readable
provenance record are in `data/tennis/`, and the dataset is released under
CC BY 4.0 with an explicit third-party-rights notice.

The trace-coverage audit proves that 600 was an operational cutoff. The first
50 train records were processed as a pilot. All 735 remaining records were
prepared in fifteen batches, but output exists only for batches 1--12 (600
records), and the pilot was never concatenated into the full file. The missing
185 are exactly the valid 50-record pilot plus the 135 requests in ungenerated
batches 13--15. No quality-filter record exists.

A targeted AI-assisted semantic review inspected 302 training records and
flagged ten wrong or underdetermined items: seven in the reported 600, none in
the pilot, and three in the ungenerated tail. This confirms a data-quality
problem while rejecting quality filtering as the cause of the 600 cutoff. The
review is risk-oriented rather than random. It remains historical evidence;
the new full audit uses two independent blinded model passes and a third model
adjudicator, with the absence of human calibration stated explicitly.

## Completed Tennis-Test Results

### 0.5B Standalone Tennis Subexperiment

These metrics are supported by committed `metrics.json`, predictions, and
evaluation run metadata under `results/tennis_domain_adaptation/scored/`.

| Condition | Model and prompt | n | EM | F1 | Malformed |
| --- | --- | ---: | ---: | ---: | ---: |
| `base_qwen_standard_test224` | Qwen2.5-0.5B, standard | 224 | 0.379 | 0.472 | 0 |
| `base_qwen_tiser_test224` | Qwen2.5-0.5B, TISER | 224 | 0.375 | 0.420 | 5 |
| `tennis_only_full600_test224` | Qwen2.5-0.5B + tennis LoRA, TISER | 224 | 0.464 | 0.516 | 0 |

The exact adapter used for the final row has been recovered from commit
`53a135a` at `model/tiser_tennis_full600_smoke/adapter`. The 8,676,008-byte
weights file has SHA-256
`01e89ffbbc939622cd9213d8150eab2bca4643f954dd26e6154496ed89cae64b`.
Portable reconstruction settings remain in
`config/config_tennis_0p5b_reported_full600.yaml`, but retraining is not needed
to audit the historical result. This is a small-model subexperiment and must
not be described as the 7B domain-adaptation result.

### 7B Tennis-from-TISER Experiments

The original TISER transfer result and the best continued-adaptation result are
supported by committed metrics. Both required adapters are present in the
current tree.

| Condition | Model and prompt | n | EM | F1 | Malformed |
| --- | --- | ---: | ---: | ---: | ---: |
| `original_tiser_qwen7b_test224` | Qwen2.5-7B + original TISER LoRA, TISER | 224 | 0.580 | 0.701 | 0 |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | Qwen2.5-7B + continued tennis LoRA, TISER | 224 | 0.728 | 0.852 | 0 |

The second row improves on the first by 0.147 EM and 0.151 F1 on the same
224-example selection set. The canonical portable settings are in
`config/config_tennis_7b_reported_best.yaml`; the training command must also
pass `--base-adapter model/tiser_qwen7b_full/adapter`.

All 22 candidates were evaluated on the same 224-record selection split,
enabling direct comparison. Continued adaptation achieved the highest
selection-set score. The selected adapter was then kept unchanged and evaluated
once on the separate 113-record holdout, where C0 reaches 0.575 EM / 0.677 F1
and C1 reaches 0.735 EM / 0.834 F1.

## Remaining limitations

- The model-judge audits have no human calibration, and the displayed GPT-5.6
  Sol label does not expose the backend snapshot or decoding settings.
- The retention interval establishes neither clear forgetting nor
  non-inferiority under the predefined margin.
- The inconclusive gate did not authorize C1R, R25, or R25-T training, so the
  study provides no replay-effectiveness comparison.
- The 21 training records flagged across the semantic and trace audits were
  present in the reported training data; their causal effect was not measured.
- Each trained adapter represents one seed, so training variability is unknown.

## Reporting Rules

- Label the 0.5B experiment and the 7B continued-adaptation experiment
  separately; they are not interchangeable.
- Cite exact condition identifiers and committed metric paths.
- State that ChatGPT-5.5 generated the dataset using the documented prompts, and
  distinguish raw-example generation from supervised trace generation.
- State that 600 is twelve completed batches, not a quality-selected or optimal
  data size.
- Do not treat the structural validator as semantic validation.
- Distinguish the 224-record selection result from the 113-record final-holdout
  result.
- State that replay was not run because the predefined retention gate was
  inconclusive; do not present replay as unfinished work.

The execution-grade continual-learning protocol is in
`FORGETTING_MIXED_REPLAY_PLAN.md`. The fully automated replacement for the
missing reflection judge is in
`../context_memory_conflict/AUTOMATED_REFLECTION_AUDIT.md`.

## Completed conditional study

The seed-42 retention sample contains 100 records from each of six
original-TISER splits. The primary five-split macro uses 500 in-domain records:
C0 reaches 0.880 EM / 0.946 F1 and C1 reaches 0.876 EM / 0.936 F1. The paired EM
difference is -0.004 with a 95% interval of [-0.028, 0.020]. The gate is
inconclusive, so no replay condition is trained. The final campaign evaluates
the unchanged C0 and C1 adapters on all 113 audited tennis-holdout records.
