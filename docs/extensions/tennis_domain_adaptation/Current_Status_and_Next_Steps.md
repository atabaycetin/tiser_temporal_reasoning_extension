# Tennis Domain Adaptation: Current Status and Next Steps

This document separates claims supported by committed artifacts from missing
provenance and future experiments. It is the source of truth for the tennis
extension; older condition names in result metadata are retained as historical
identifiers.

The completion protocol is now implemented. The active GPT-5.6 Sol audit target is
`results/project_audit_v2/progress.json`; create it with the preparation command
in `docs/PROJECT_AUDIT_EXECUTION.md`. The conditional GPU workflow is
`notebooks/colab_conditional_retention.ipynb`. Neither partial judgments nor
notebook smoke runs are reportable outcomes.

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
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | Qwen2.5-7B + continued tennis LoRA, TISER | 224 | 0.732 | 0.856 | 0 |

The second row improves on the first by 0.152 EM and 0.155 F1 on the same
224-example test set. The canonical portable settings are in
`config/config_tennis_7b_reported_best.yaml`; the training command must also
pass `--base-adapter model/tiser_qwen7b_full/adapter`.

However, the winning condition was selected by ranking 22 distinct candidate
adapters on that test split. Choosing the maximum of several noisy test
scores makes the selected value optimistic. The conventional procedure would
select on `tennis_dev.json`, lock one configuration, and use an untouched test
set once. Because the current test was already used for selection, merely
rerunning the grid on development cannot erase that information leak. The
implemented protocol follows option 2 below. No prior model-performance use of
the 113 records is known, while the repository cannot exclude an unrecorded
evaluation. The alternatives were:

1. label 0.732/0.856 as the best observed exploratory test result;
2. because no preserved model-performance artifact uses the 113-record
   development split, freeze this adapter and evaluate it there once,
   relabelling that split as the final holdout (subject to the possibility of
   an unlogged manual run); or
3. after cleaning the data, select a new run on development and evaluate once
   on a newly reserved final holdout.

Option 2 does not require rerunning hyperparameter search. It gives a smaller
but clean estimate for the already selected adapter. Once inspected, that
113-record split must not be used to choose a different configuration.

## Not Yet Supported

The following claims or procedures do not have all required evidence in the
current repository:

- A complete semantic adjudication of the raw examples and traces. The current
  302-record review is targeted and flags candidates; it is not a full human
  certification.
- A complete semantic validation of the trace contents. Two hundred outputs
  were wrapped to restore tags, and 26 objects were repaired from 19 malformed
  physical lines; structural repair does not establish temporal correctness.
- Mixed tennis plus original-TISER replay results remain absent. The historical
  canonical destination was `model/tiser_tennis_mixed_replay_qwen7b/adapter`;
  the new registry will instead record R25 under its frozen study directory only
  if the forgetting gate shows clear forgetting. R25-T remains absent unless its
  token gate fires.
- Forgetting or preservation results on an original TISER evaluation sample.
- A final performance estimate from data untouched by hyperparameter selection.

## Reporting Rules

- Label the 0.5B experiment and the 7B continued-adaptation experiment
  separately; they are not interchangeable.
- Cite exact condition identifiers and committed metric paths.
- State that ChatGPT-5.5 generated the dataset using the documented prompts, and
  distinguish raw-example generation from supervised trace generation.
- State that 600 is twelve completed batches, not a quality-selected or optimal
  data size.
- Do not treat the structural validator as semantic validation.
- Call the selected 7B test score exploratory unless it is confirmed on a new
  untouched holdout.
- Treat mixed replay and forgetting as future work unless new artifacts are
  added and audited.

The execution-grade continual-learning protocol is in
`FORGETTING_MIXED_REPLAY_PLAN.md`. The fully automated replacement for the
missing reflection judge is in
`../context_memory_conflict/AUTOMATED_REFLECTION_AUDIT.md`.

## Active Remaining Execution

1. Complete both blinded passes over all 1,121 unique semantic items, 650
   traces, and 2,295 scorable reflections; adjudicate every disagreement and
   every proposed gold correction.
2. Freeze versioned tennis evaluation sidecars. Unresolved or underdetermined
   records stay in the original files and are excluded only from the primary
   scoring denominator.
3. Run C0 and C1 on the frozen original-TISER selection population. Train C1R
   and R25 only if the preregistered interval shows clear forgetting, and run
   R25-T only if supervised-token exposure differs by more than 10%.
4. Freeze the applicable conditions and run one final campaign on the 113
   original tennis inputs and the exact original-TISER complement. Preserve
   original-label tennis scores as the secondary historical view.
5. Update result tables only from completed, hash-validated artifacts. Continue
   to state that the model-judge audit has no human calibration and that
   historical UI snapshot/decoding settings are unavailable.
