# Implementation audit - 2026-09-08

> **Superseded status record.** This file preserves the state observed on
> 2026-09-08 and is not a list of pending work. Current completed results are
> documented in
> `docs/extensions/tennis_domain_adaptation/Current_Status_and_Next_Steps.md`.
> The original-TISER complement evaluation described below is not part of the
> completed workflow and will not be run.

> Historical checkpoint: the coverage below describes the incomplete
> `project_audit_v1` attempt. Its model provenance does not satisfy the current
> GPT-5.6 Sol requirement. The active procedures use independent reflection,
> semantic, and trace audit directories and do not relabel or reuse v1 judgments.

## Status

The repository contains the planned controls for the full dataset and
reflection audits, conditional retention/replay experiment, and final holdout
campaign. The scientific work is not complete: the file audit is still in
progress, and no new 7B inference or training has run.

Current accepted coverage:

| Audit | Completed unique items | Total unique items |
| --- | ---: | ---: |
| Tennis semantics | 125 | 1,121 (mapping to 1,122 rows) |
| Tennis traces | 30 | 650 |
| Reflections | 200 | 2,295 |

The accepted ledger also contains 22 completed adjudications. Partial coverage
is not reported as a population estimate.

## Implemented controls

### Dataset and reflection audits

- `scripts/audit.py` prepares blinded file batches, imports complete responses,
  creates adjudication batches, summarizes completed judgments, and freezes
  scoring views.
- Semantic records, traces, and reflections receive two independent passes.
  Label disagreements and proposed answer corrections require adjudication.
- Imports validate batch membership, source hashes, schemas, labels, and exact
  evidence quotations before accepting a response.
- Historical inputs remain unchanged. Completed decisions produce versioned
  eligibility and gold sidecars for evaluation.
- Reflection summaries retain all 1,176 rows per condition and report
  disagreement, unscorable counts, control false positives, conflict classes,
  Wilson intervals, and silent overrides. Human calibration is unavailable and
  remains a stated limitation.

### Retention, replay, and final evaluation

- The original TISER release is pinned to revision
  `7bdac51ea363a71b1805972b1d2c025f5cd173a4`. Its 22,014 evaluation rows are
  partitioned into a seed-42 selection set of 600 and a disjoint final
  complement of 21,414.
- C0 and C1 are evaluated on the selection set. Their paired five-split
  macro-EM interval determines whether training stops or proceeds to C1R and
  R25. R25-T runs only if replay changes supervised-token exposure by more than
  10 percent.
- Current training conditions start from the same verified C0 adapter and share
  the model revision, environment, GPU, seed, LoRA settings, optimizer schedule,
  and 74-update budget.
- Training records consumed examples, non-padding tokens, supervised targets,
  microbatches, and completed optimizer updates. Checkpoint resume restores
  optimizer, scheduler, random state, trainer state, and token counters.
- Evaluation fixes ordered IDs, gold answers, prompts, data, adapter, resolved
  configuration, environment, and optional audited scoring view. Predictions
  are stored in resumable 64-row chunks.
- The final campaign remains unavailable until the audits and applicable
  selection stages are complete. It then evaluates the fixed conditions once
  on the 113 tennis holdout records and original-TISER complement.

### Statistics and Colab execution

- Paired reports include EM/F1 differences, 10,000 seed-42 bootstrap samples,
  McNemar tables, and Holm-adjusted EM tests. The five-split retention macro
  excludes ToT-semantic, which is reported separately.
- `notebooks/colab_conditional_retention.ipynb` separates preparation,
  selection evaluation, the forgetting decision, conditional training, audit
  freeze, final evaluation, and statistics. Persistent outputs live in Drive.
- `scripts/prepare_study_bundle.py` regenerates the direct-Drive notebook and
  validates every code cell before writing it.

## Corrections made during interruption recovery

- Audit responses are now accepted atomically: one invalid or missing item
  rejects the complete response. Earlier affected entries were removed from the
  accepted ledger; the original response and repair record remain preserved.
- Prediction persistence was changed from one file per four generated rows to
  64-row chunks to reduce Drive operations without increasing GPU batch size.
- The notebook now detects and rejects a stale extracted workspace after its
  Drive bundle changes.
- Bundle creation excludes bytecode, hidden metadata, and quarantined judge
  responses.
- Registry paths are relative to the study or workspace so completed Colab
  results remain resolvable after transfer.
- Incomplete training can be archived and restarted without deleting the failed
  attempt.

## Verification

- System Python: 79 tests passed and one NumPy-dependent statistics test was
  skipped.
- The skipped statistics path passed with the bundled NumPy runtime and produced
  repeatable 10,000-sample results.
- Historical tennis data, both historical adapters, and the pinned original
  TISER files match their recorded hashes.
- The 600/21,414 retention partition is unique, disjoint, complete, and stable
  across repeated preparation.
- The Colab notebook contains no saved outputs, and all code cells compile.
- No 7B inference, training, retention evaluation, or tennis holdout evaluation
  was run on the MacBook.

## Next execution steps

1. Complete both audit passes and all resulting adjudications.
2. Freeze the audited scoring views.
3. Run the Colab selection evaluation and forgetting decision.
4. Run C1R/R25 and, if triggered, R25-T.
5. Freeze and execute the final campaign once.
6. Update the report only from the completed artifacts.

Operational commands are documented in `docs/PROJECT_AUDIT_EXECUTION.md` and
the experimental protocol is in
`docs/extensions/tennis_domain_adaptation/FORGETTING_MIXED_REPLAY_PLAN.md`.
