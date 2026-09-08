# Conditional Retention and Replay Study

## Scope

This workflow completes the final 113-record evaluation, measures retention on
the original TISER tasks, and trains replay conditions only if the fixed gate
detects forgetting. If training is triggered, it adds a contemporary
tennis-only control and measures supervised-token exposure so the replay
comparison is not explained by a larger training budget. Historical settings
that cannot be recovered remain explicitly unknown. The semantic, trace, and
reflection audits must finish before final evaluation.

The registered conditions are C0, C1, conditional C1R and R25, and conditional
R25-T. Additional replay ratios and a corrected-data ablation are not part of
this study.

## Implemented interfaces

- `scripts/experiment.py` coordinates initialization, population preparation,
  evaluation, the forgetting gate, conditional data construction/training, the
  token gate, final-campaign freezing, and paired statistics.
- `scripts/paired_statistics.py` runs the same strict paired-statistics engine
  from a standalone comparison specification.
- `scripts/tennis/fetch_retention_data.py` fetches and verifies the upstream
  release at Git revision `7bdac51ea363a71b1805972b1d2c025f5cd173a4`.
- `notebooks/colab_conditional_retention.ipynb` invokes those interfaces in
  resumable stages and writes checkpoints/results to Drive.
- `scripts/prepare_study_bundle.py` creates the notebook and a portable bundle
  containing source, tests, historical adapters, tennis data, and audit state.

The coordinator records source/config hashes, dirty Git state, historical data,
adapter trees, input populations, prompt/config manifests, predictions, and
statistics. Provenance distinguishes directly observed values, information
recorded by the team, derived values, and unavailable values. Historical UI
model snapshots and decoding settings remain unavailable.

Registry paths are scope-qualified. Files inside the Drive study resolve from
the study root, repository inputs resolve from the workspace root, and truly
external paths are labelled explicitly. A completed study can therefore be
copied back without retaining broken `/content/...` artifact references.

## Conditions and execution rule

| Condition | Definition | Rule |
| --- | --- | --- |
| C0 | Existing original-TISER adapter | Always evaluated |
| C1 | Existing historical tennis winner | Always evaluated and never switched |
| C1R | Fresh current run on the historical 600 tennis traces | Train only after clear forgetting |
| R25 | The same 600 tennis traces plus 200 original-TISER train rows | Train only after clear forgetting |
| R25-T | R25 with the completed-update boundary nearest C1R supervised tokens | Train only when R25 differs from C1R by more than 10% |

C1R and R25 start from the verified C0 adapter and use one GPU, seed 42,
4-bit loading, LoRA rank 16/alpha 32/dropout 0.05, batch 4 with accumulation 4,
learning rate 2e-4, cosine scheduling, 0.03 warmup, a 2,048-token limit, and 74
optimizer updates. The registry rejects different contemporary software or GPU
environments. R25-T changes only the number of completed updates needed for the
token-matched sensitivity run.

## Frozen populations and forgetting gate

`prepare-data` deterministically creates a seed-42 sample of up to 100 rows from
each upstream test split and its exact complement. Invalid repeated identifiers
in the ToT-semantic OOD split receive derived, source-row-addressed identifiers;
the upstream file remains unchanged. The five in-domain benchmark splits define
the retention macro, while ToT-semantic remains separate OOD evidence.

C0 and C1 are evaluated on the selection sample. Ten thousand stratified paired
bootstrap resamples (seed 42) produce the 95% interval for the five-split macro
EM difference `C1 - C0`:

- upper bound below -0.02: clear forgetting; train C1R and R25;
- lower bound above -0.02: non-inferior retention; stop training;
- otherwise: inconclusive; stop training.

This decision is frozen and cannot be reopened by later scores.

## Replay construction and exposure accounting

Replay rows come only from the pinned original-TISER training release. The
builder rejects evaluation overlap, tennis overlap, duplicate prompts, missing
or placeholder traces, invalid trace tags, trace/gold disagreement, and rows
over 2,048 tokens. It requires exactly 600 tennis plus 200 accepted original
rows and records every rejected candidate and final ordered identifier.

Training counts examples, non-padding input tokens, supervised next-token
targets, microbatches, and cumulative totals at each optimizer update, including
repeated exposures. Checkpoints contain optimizer, scheduler, RNG state, token
ledger, trainer state, and frozen training specification. A complete output can
be registered after an interrupted coordinator step. An incomplete pre-checkpoint
attempt can be moved intact to `failed_attempts/` with `--restart-incomplete`.

## Final campaign

Final freezing requires complete two-pass/adjudicated semantic, trace, and
reflection audits plus all applicable selection diagnostics. It freezes every
condition, input, audited scoring view, prompt/parser/metric source snapshot,
model revision, and selection prediction.

- Without clear forgetting, final conditions are C0 and C1.
- With clear forgetting, final conditions are C0, C1, C1R, and R25, plus R25-T
  when the token gate requires it.

Each condition is generated once, with resumable immutable chunks, on the 113
original tennis inputs and the original-TISER complement. The audited tennis
gold/eligibility view is primary; the original labels remain a secondary
historical view. The campaign records that the team has no record of prior use,
while noting that repository evidence alone cannot establish this. Final
outcomes cannot trigger adapter switching, tuning, or new training.

Paired output validation requires identical ordered IDs, gold versions, and
scoring-view hashes. Results include EM/F1 differences, paired bootstrap
intervals, exact McNemar tables, and Holm-adjusted EM tests. Tennis
non-inferiority requires the lower paired bound to exceed -0.02. All training
results use one seed, so training variability remains unmeasured.

GPU generation uses memory-safe model batches, while completed predictions are
persisted to Drive in 64-row immutable chunks. This avoids creating one Drive
file per four-row generation batch; interruption can require regenerating at
most the uncommitted tail of 63 rows.

## Colab execution

Generate the handoff after local tests and audit imports:

```bash
python3 scripts/prepare_study_bundle.py
```

Place `output/tiser_study_workspace.zip` in Drive, open
`notebooks/colab_conditional_retention.ipynb`, select one CUDA GPU, and run cells
in order. The notebook stops before final freezing while any audit item is
pending. Re-running a cell resumes only validated prediction chunks or complete
training checkpoints.

The extracted `/content` workspace is ephemeral. After replacing the Drive zip
with a bundle containing additional completed audit responses, start a fresh
runtime or delete only `/content/tiser_temporal_reasoning_extension` and rerun
the setup cell. Preserve `/content/drive/MyDrive/tiser_conditional_study_v2` so
validated predictions and checkpoints remain available. The setup cell detects
a changed bundle and stops instead of silently mixing source snapshots.

No retention, replay, or final-holdout outcome exists until the corresponding
frozen artifacts are produced. Documentation and the report must not substitute
partial audit coverage or smoke results for those outcomes.
