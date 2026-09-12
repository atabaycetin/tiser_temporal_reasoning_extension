# TISER Temporal-Reasoning Reproduction and Extensions

This repository reproduces **TISER** (Bazaga, Blloshmi, Byrne, and de
Gispert, ACL 2025, [arXiv:2504.05258](https://arxiv.org/abs/2504.05258)) and
implements two distinct extensions:

1. **Context-memory conflict:** an inference-time robustness probe with no new
   training. It tests whether a model follows an edited context when the context
   contradicts the model's elicited memory.
2. **Tennis domain adaptation:** supervised continued training on tennis
   temporal-QA traces, followed by transfer evaluation on a held-out tennis
   test set.

TISER fine-tunes an instruction model on a structured target containing
`<reasoning>`, `<timeline>`, `<reflection>`, and `<answer>` sections. At
inference, the model generates the trace once and the evaluator extracts the
answer for exact-match (EM) and token-F1 scoring.

## Repository map

| Path | Contents |
| --- | --- |
| `config/config.yaml` | Reported 7B baseline training and full-evaluation settings |
| `config/config_smoke.yaml` | 1.5B baseline plumbing smoke test |
| `config/conflict.yaml` | Context-memory conflict pipeline settings |
| `config/config_tennis_smoke.yaml` | 0.5B, 50-trace tennis smoke test |
| `config/config_tennis_0p5b_reported_full600.yaml` | Portable settings for the reported 0.5B/600-trace result |
| `config/config_tennis_7b_reported_best.yaml` | Portable settings for the best reported 7B continued-adaptation result |
| `src/` | Data, model, training, inference, evaluation, conflict, and tennis modules |
| `scripts/` | Command-line entry points; every command supports `--help` |
| `scripts/audit.py` | Offline coordinator for separate two-pass semantic, trace, or reflection audits |
| `scripts/experiment.py` | Frozen conditional retention/replay and final-campaign coordinator |
| `notebooks/colab_conditional_retention.ipynb` | Resumable single-GPU Colab execution notebook |
| `data/tennis/` | Tennis data, dataset card, provenance record, and CC BY 4.0 licence |
| `results/` | Committed result snapshots and run metadata |
| `outputs/` | Gitignored outputs produced by new runs |
| `model/` | Selected committed LoRA adapters |
| `report/` | IEEE LaTeX report and figures |

Run commands from the repository root. Relative paths in YAML files are
resolved against the repository root, except `local_source_dir`, which is an
optional repo-root working-directory path used only by the data-fetch command.

## Environment

Python 3.10 or newer is required; development used Python 3.11. The repository
intentionally does not pin PyTorch because its build must match the host CUDA
runtime.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "torch>=2.3"
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pip install pytest matplotlib
```

On Colab, keep the bundled CUDA-compatible PyTorch and omit the separate torch
installation. The pinned training stack is documented in `requirements.txt`.
The full baseline evaluation artifact used vLLM 0.22.0 in a separate inference
environment; vLLM is intentionally not installed by `requirements.txt` because
it may require a different PyTorch/Transformers combination. Use the HF engine
for compatibility, or install a CUDA-matched vLLM release in a separate
environment for the faster reported evaluation path.

CPU-only commands include dataset audit/build/split, trace validation, scoring,
result comparison, statistics, tests, and report compilation. Model training,
memory elicitation, and generation require a CUDA GPU. The committed 7B
baseline run took about 6.5 hours on one H200 SXM with bf16 LoRA; an 80 GB
A100/H100-class GPU is the practical target. The 7B tennis runs use 4-bit model
loading and can run on smaller GPUs with reduced batch size. The 0.5B smoke
path is substantially lighter.

## CLI discovery

The repository exposes script-based CLIs rather than installed console-command
aliases. Inspect any interface before running it:

```bash
python scripts/train.py --help
python scripts/evaluate.py --help
python scripts/conflict/01_build_subset.py --help
python scripts/tennis/train_tennis.py --help
python scripts/tennis/evaluate_tennis.py --help
python scripts/audit.py --help
python scripts/experiment.py --help
```

Main entry points:

| Workflow | Commands |
| --- | --- |
| Baseline | `scripts/fetch_data.py`, `scripts/train.py`, `scripts/evaluate.py` |
| Conflict probe | `scripts/conflict/01_build_subset.py` through `08_stats.py` |
| Tennis data | `audit_tennis_raw.py`, `build_tennis_data.py`, `split_tennis_data.py` |
| Tennis traces | `prepare_tennis_trace_generation.py`, `merge_tennis_traces.py`, `validate_tennis_traces.py` |
| Tennis experiment | `train_tennis.py`, `evaluate_tennis.py`, `compare_adapters.py` |

Installed aliases are not declared in `pyproject.toml`: the wrappers live under
`scripts/`, which is not an installed package, and their callable functions do
not share a stable argument-forwarding interface. Direct script invocation is
therefore the portable supported CLI.

## Baseline reproduction

### Smoke test

This exercises fetch, 4-bit training, adapter output, generation, and scoring on
small subsets. It validates plumbing and is not an accuracy result.

```bash
python scripts/fetch_data.py --config config/config_smoke.yaml
python scripts/train.py --config config/config_smoke.yaml
python scripts/evaluate.py --config config/config_smoke.yaml
```

Expected outputs:

```text
data/TISER_train.json
data/TISER_test.json
model/tiser_smoke/adapter/
outputs/tiser_smoke/
outputs/tiser_smoke/metrics.json
```

Use the terminal's final `wrote` message as the authoritative path if a custom
output directory is supplied.

### Full reported baseline

`config/config.yaml` selects the full training file, three epochs, bf16 LoRA,
and no train/evaluation subsampling. Data fetch first checks `data/`, then
optional `local_data/`, then the Hugging Face mirror, and finally upstream Git
LFS.

```bash
python scripts/fetch_data.py --config config/config.yaml
python scripts/train.py --config config/config.yaml
python scripts/evaluate.py \
  --config config/config.yaml \
  --adapter-dir model/tiser_qwen7b_full/adapter \
  --eval-engine vllm
```

Use `--eval-engine hf` if vLLM is unavailable; greedy decoding remains
deterministic, but library/backend differences are recorded in run metadata.
The committed full-test metrics are in
`results/baseline/tiser_qwen7b_full/metrics.json`: macro-EM 0.8778 and macro-F1
0.9486 over the five in-domain splits. The 2,800-example ToT-semantic OOD split
is reported separately and excluded from the macro.

## Context-memory conflict extension

This extension is an inference-time probe, not a training procedure. New runs
write to `outputs/conflict/<stage>/`; the corresponding committed snapshots are
under `results/context_memory_conflict/`.

Run stages in order:

```bash
python scripts/fetch_data.py --config config/conflict.yaml
python scripts/conflict/01_build_subset.py --config config/conflict.yaml
python scripts/conflict/02_elicit_memory.py --config config/conflict.yaml
python scripts/conflict/03_filter_eligible.py --config config/conflict.yaml
python scripts/conflict/04_build_conflicts.py --config config/conflict.yaml
python scripts/conflict/04b_build_run_inputs.py --config config/conflict.yaml

python scripts/conflict/05_run_inference.py --config config/conflict.yaml --model base --style standard
python scripts/conflict/05_run_inference.py --config config/conflict.yaml --model base --style tiser
python scripts/conflict/05_run_inference.py --config config/conflict.yaml --model tiser --style standard
python scripts/conflict/05_run_inference.py --config config/conflict.yaml --model tiser --style tiser

python scripts/conflict/06_score.py --config config/conflict.yaml --model base --style standard
python scripts/conflict/06_score.py --config config/conflict.yaml --model base --style tiser
python scripts/conflict/06_score.py --config config/conflict.yaml --model tiser --style standard
python scripts/conflict/06_score.py --config config/conflict.yaml --model tiser --style tiser
python scripts/conflict/08_stats.py --config config/conflict.yaml --seed 42
```

Stages 01, 03, 04, 04b, 06, and 08 are CPU-capable. Stages 02 and 05 require
model inference; the committed configuration uses vLLM and the adapter at
`model/tiser_qwen7b_full/adapter`.

The committed set has 1,056 genuine conflict rows (C1/C2/C3) and 120
answer-preserving controls. The aggregate 1,176-row faithful-EM changes from
0.3801 for base+standard to 0.7866 for TISER+TISER. Controls should be reported
separately from genuine conflicts.

`scripts/conflict/07_confidence_vs_reflection.py` is not part of the fresh-clone
command sequence because it requires
`outputs/conflict/scored/audit/*.audit.csv`. Those LLM-judge CSVs, the exact
judge prompt, and judge model settings are not committed. Consequently, the
report's 4.3% genuine-conflict reflection rate cannot currently be regenerated
from this repository. Run stage 07 only after those artifacts and their
provenance have been restored.

## Tennis domain-adaptation extension

### Auditable data-processing pipeline

These commands reproduce the stages that are supported by code and tracked
inputs:

```bash
python scripts/tennis/audit_tennis_raw.py \
  --input data/tennis/raw/tennis_raw.json \
  --output data/tennis/processed/tennis_raw_audited.json \
  --report results/tennis_domain_adaptation/raw_audit/tennis_raw_audit_report.md \
  --summary results/tennis_domain_adaptation/raw_audit/tennis_raw_audit_summary.json

python scripts/tennis/build_tennis_data.py \
  --input data/tennis/processed/tennis_raw_audited.json \
  --output-dir data/tennis/processed \
  --summary-dir results/tennis_domain_adaptation/processed \
  --deterministic-output \
  --prompt-version reported

python scripts/tennis/split_tennis_data.py \
  --input data/tennis/processed/tennis_all_tiser.json \
  --output-dir data/tennis \
  --train-ratio 0.7 \
  --dev-ratio 0.1 \
  --test-ratio 0.2 \
  --seed 42
```

Expected counts are 1,122 converted records and 785/113/224 train/dev/test
records. Splitting is deterministic, category-aware, and duplicate-group aware.
With `--prompt-version reported`, the builder preserves the historical prompt
used for the reported training runs and byte-reproduces the tracked converted
records and split files. The default `--prompt-version strict` uses the newer
explicit XML-answer instruction for new experiments. Record the selected mode
and do not mix prompt versions within an experiment.

The collection is synthetic. ChatGPT-5.5 generated the 1,122 raw records using
the raw-example prompt included in the report appendix and
`RAW_GENERATION_PROMPT.md`. It then generated supervised TISER traces from
training examples and their supplied gold answers using the trace-generation
prompt. The two-stage workflow is recorded in `data/tennis/DATASET_CARD.md`,
`data/tennis/PROVENANCE.json`, and
`docs/extensions/tennis_domain_adaptation/RAW_GENERATION_PROMPT.md`. The data
are released under CC BY 4.0; scope, attribution, and third-party-rights caveats
are in `data/tennis/DATASET_LICENSE.md`.

Prepare prompts for offline trace generation:

```bash
python scripts/tennis/prepare_tennis_trace_generation.py \
  --input data/tennis/tennis_train.json \
  --output-dir outputs/tennis/trace_requests \
  --exclude-files data/tennis/tennis_train_traced_50.json \
  --batch-size 50 \
  --limit all
```

This command only creates prompts and a manifest; it calls no model or external
API. ChatGPT-5.5 generated the traces in a separate supervised step using the
documented trace-generation prompt. Every request supplied the context,
question, and gold answer. The prompt, artifact structure, repair history, and
a stricter prompt for future runs are in
`docs/extensions/tennis_domain_adaptation/TRACE_GENERATION_PROMPT.md`.

Given the committed generation rows, the 600-record training artifact can be
reconstructed and checked without overwriting it:

```bash
python scripts/tennis/merge_tennis_traces.py \
  --source data/tennis/tennis_train.json \
  --generated results/tennis_domain_adaptation/trace_generation/generated_traces_full.jsonl \
  --output outputs/reproduced/tennis_train_traced_full.json \
  --failed-output outputs/reproduced/tennis_trace_merge_failures.json

python scripts/tennis/validate_tennis_traces.py \
  --input outputs/reproduced/tennis_train_traced_full.json \
  --failed-output outputs/reproduced/tennis_trace_validation.json
```

Reproduce the coverage audit that explains the 600-record cutoff:

```bash
python scripts/tennis/audit_tennis_trace_coverage.py
```

The result is exact: the 785-record train pool partitions into a traced pilot
at positions 0--49, the reported 600 at positions 50--649 (exactly batches
1--12), and 135 prepared but ungenerated requests at positions 650--784
(batches 13--15). The pilot was not concatenated into the full file. Thus the
repository has 650 unique traced train records, while the reported adaptations
use the disjoint 600-record artifact. The 113 development and 224 test records
have no supervised traces and never enter gradient updates. The full 785 is
retained because it is the canonical training partition of the 1,122-record
dataset; deleting pilot or ungenerated rows would erase experiment lineage and
split coverage without changing what the trainer reads.

A targeted AI-assisted semantic review of 302/785 training records found ten
wrong or underdetermined examples: seven inside the reported 600 and three in
the ungenerated tail. This confirms that quality problems exist but rejects the
claim that removing them produced the 600-record set. The auditable selection
method and findings are under
`results/tennis_domain_adaptation/semantic_audit/`. Do not edit the historical
data in place. Complete the planned two-pass audit and automated adjudication,
record the absence of human calibration, then create a versioned clean dataset
and regenerate affected traces.

### 0.5B reported subexperiment

The exact historical adapter that produced the committed result is available
at `model/tiser_tennis_full600_smoke/adapter`. It was recovered from Git commit
`53a135a`; its 8,676,008-byte weights file has SHA-256
`01e89ffbbc939622cd9213d8150eab2bca4643f954dd26e6154496ed89cae64b`.
Retraining is therefore unnecessary for auditing the historical result.

Evaluate that adapter without overwriting committed results:

```bash
python scripts/tennis/evaluate_tennis.py \
  --config config/config_tennis_0p5b_reported_full600.yaml \
  --test-file data/tennis/tennis_test.json \
  --no-adapter \
  --condition base_qwen_standard_reproduced \
  --prompt-style standard \
  --output-dir outputs/reproduced/tennis_0p5b/base_standard

python scripts/tennis/evaluate_tennis.py \
  --config config/config_tennis_0p5b_reported_full600.yaml \
  --test-file data/tennis/tennis_test.json \
  --adapter-dir model/tiser_tennis_full600_smoke/adapter \
  --condition tennis_only_full600_historical_restored \
  --prompt-style tiser \
  --output-dir outputs/reproduced/tennis_0p5b/historical_restored
```

The supported historical comparison is EM/F1 0.379/0.472 for standard base
prompting versus 0.464/0.516 for the tennis-only adapter. Exact adapter bytes
are restored, but regenerated answers can still vary across GPU and library
versions.

To train a new reconstruction instead of using the original adapter:

```bash
python scripts/tennis/train_tennis.py \
  --config config/config_tennis_0p5b_reported_full600.yaml
```

This is 600 optimizer steps on a 0.5B model. Historical timestamps bound the
original training plus model reload and 100-example generation to under eight
minutes on one unrecorded CUDA GPU. Allow roughly 5--20 minutes on a modern
NVIDIA GPU after download; 8 GB VRAM is likely sufficient and 16 GB is safer.
This estimate is not a benchmark for the present machine.

### 7B reported continued adaptation

The best committed condition trained for two epochs on the 600 traced records,
starting from the original TISER adapter:

```bash
python scripts/tennis/train_tennis.py \
  --config config/config_tennis_7b_reported_best.yaml \
  --base-adapter model/tiser_qwen7b_full/adapter
```

Evaluate the two already committed adapters:

```bash
python scripts/tennis/evaluate_tennis.py \
  --config config/config_tennis_7b_reported_best.yaml \
  --test-file data/tennis/tennis_test.json \
  --adapter-dir model/tiser_qwen7b_full/adapter \
  --condition original_tiser_qwen7b_reproduced \
  --prompt-style tiser \
  --output-dir outputs/reproduced/tennis_7b/original_tiser

python scripts/tennis/evaluate_tennis.py \
  --config config/config_tennis_7b_reported_best.yaml \
  --test-file data/tennis/tennis_test.json \
  --adapter-dir model/tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011/adapter \
  --condition tennis_from_tiser_best_reproduced \
  --prompt-style tiser \
  --output-dir outputs/reproduced/tennis_7b/continued_adaptation
```

The fixed 224-example rerun gives EM/F1 0.580/0.701 for the original TISER
adapter and 0.728/0.852 for the continued-adaptation adapter. All 22 candidates
were evaluated on the same 224-record selection split, enabling direct
comparison, and continued adaptation achieved the highest selection-set score.
The selected adapter was then kept unchanged and evaluated once on the separate
113-record holdout. That final evaluation gives 0.575/0.677 for the original
TISER adapter and 0.735/0.834 for continued adaptation. Reflection and trace
audits have separate outputs and do not block this evaluation.

Regenerate a comparison table directly from the committed result artifacts:

```bash
python scripts/tennis/compare_adapters.py \
  --condition-dirs \
    results/tennis_from_tiser_experiments/scored/original_tiser_qwen7b_test224 \
    results/tennis_from_tiser_experiments/scored/tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011 \
  --baseline original_tiser_qwen7b_test224 \
  --output-dir outputs/reproduced/tennis_7b/comparison
```

Expected outputs are `adapter_comparison.{json,md,csv}` and
`per_category_comparison.csv` in that directory.

The full evidence/limitation ledger is
`docs/extensions/tennis_domain_adaptation/Current_Status_and_Next_Steps.md`.

The rigorous new-contribution protocol for measuring original-TISER retention
and, when justified, training compute-matched replay conditions is in
`docs/extensions/tennis_domain_adaptation/FORGETTING_MIXED_REPLAY_PLAN.md`.

## Separate offline audits

The reflection, tennis semantic, and tennis trace audits are separate GPT-5.6
Sol file-batch studies. Prepare only the study you intend to run:

```bash
python3 scripts/audit.py prepare --kind reflection \
  --output-dir results/reflection_audit --requested-model gpt-5.6-sol
python3 scripts/audit.py prepare --kind semantic \
  --output-dir results/tennis_semantic_audit_v2 --requested-model gpt-5.6-sol
python3 scripts/audit.py prepare --kind trace \
  --output-dir results/tennis_trace_audit_v2 --requested-model gpt-5.6-sol
```

The reflection study alone replaces the unavailable Claude aggregate. The
semantic study creates audited tennis scoring views. The trace study documents
training-data quality. Each has its own import, adjudication, summary, and
progress artifacts; one study never blocks another. Batch instructions,
validation rules, commands, and the absence of human calibration are documented
in `docs/PROJECT_AUDIT_EXECUTION.md`. One Codex task processes the complete Judge
A bundle and a separate task processes the complete Judge B bundle; each pass is
bulk-imported with one command. A literal operator runbook for the Claude
replacement is in `docs/REFLECTION_AUDIT_RUNBOOK.md`. The optional API and file-batch interfaces
share the same reflection rubric and validation code; results from one study are
never silently substituted for the other.

## Conditional retention, replay, and final evaluation

The study first evaluates C0 and C1 on a frozen seed-42 original-TISER selection
sample. Replay training occurs only when the paired 95% macro-EM interval shows
clear forgetting. A non-inferior or inconclusive gate performs no new training.
When triggered, C1R and R25 share the current environment and 74-update schedule;
R25-T runs only when supervised-token exposure differs by more than 10%.

Regenerate the checked-in notebook after editing its generator:

```bash
python3 scripts/prepare_study_bundle.py
```

The notebook mounts Google Drive and uses the repository already synchronized at
`/content/drive/Othercomputers/My Mac/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension`.
It writes persistent artifacts under
`results/forgetting_replay/study_v2` in that repository. Run
`notebooks/colab_conditional_retention.ipynb` in order on one CUDA GPU. The
workflow resumes predictions and checkpoints, preserves token counts and random
state, and blocks final evaluation until the semantic audit and selection
diagnostics are complete. The exact gate, conditions, statistics, and recovery
commands are in
`docs/extensions/tennis_domain_adaptation/FORGETTING_MIXED_REPLAY_PLAN.md`.

## Report build

Regenerate the conflict figures directly from committed metric/statistics JSON:

```bash
python scripts/report/generate_conflict_figures.py
```

This writes vector PDF and 600-dpi PNG versions of
`conflict_run_matrix` and `conflict_per_class` under `report/figures/`. The
tennis result table is backed by the `compare_adapters.py` command above; the
baseline table is backed by `results/baseline/tiser_qwen7b_full/metrics.json`.

Build the IEEE report from its directory so figure paths resolve correctly:

```bash
cd report
latexmk -pdf -interaction=nonstopmode -halt-on-error DNLP_Temporal_Reasoning.tex
```

If `latexmk` is unavailable, run `pdflatex` twice with the same
`-interaction=nonstopmode -halt-on-error` options, or run
`tectonic DNLP_Temporal_Reasoning.tex`.

## Completed execution status

- `results/reflection_audit/progress.json`,
  `results/tennis_semantic_audit_v2/progress.json`, and
  `results/tennis_trace_audit_v2/progress.json` record the completed GPT-5.6 Sol
  judgments and adjudications. Audited scoring views depend only on the semantic
  audit.
- On the predefined original-TISER retention sample, C0 reaches 0.880 macro-EM
  and C1 reaches 0.876. The paired difference is -0.004 with a 95% interval of
  [-0.028, 0.020], so the gate is inconclusive and no replay condition is trained.
- On the 113-record tennis holdout, C0 reaches 0.575 EM / 0.677 F1 and C1 reaches
  0.735 EM / 0.834 F1. These final results do not reopen model selection or training.
- Human calibration is unavailable and is reported as a limitation. Historical
  generation snapshots and decoding settings also remain unavailable; new runs
  record their actual provenance without filling those gaps by inference.

## Licenses

Repository software is released under the MIT License in `LICENSE`. The tennis
dataset and its derived trace files under `data/tennis/` are separately released
under CC BY 4.0 in `data/tennis/DATASET_LICENSE.md`. The dataset-specific notice
controls for those files.
