---
base_model: Qwen/Qwen2.5-7B-Instruct
library_name: peft
---

# Three-Epoch Tennis-from-TISER Qwen2.5-7B LoRA Adapter

This PEFT LoRA adapter is a historical three-epoch tennis continued-adaptation
candidate. Training began from the repository's TISER 7B adapter and continued
on the 600-record tennis trace artifact. It was evaluated during model selection
but was not the selected final adapter.

## Intended use

Use this artifact to inspect or reproduce the historical 7B candidate sweep.
For the selected continued-adaptation condition, use
`model/tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011/adapter`.
This adapter is not intended for factual tennis lookup or safety-critical use.

## Training

- Base model: `Qwen/Qwen2.5-7B-Instruct`, loaded in 4-bit NF4.
- Initialization: the original TISER LoRA adapter.
- Data: all 600 records in `data/tennis/tennis_train_traced_full.json`.
- Seed 42; three epochs; batch size 4 with four accumulation steps; maximum
  sequence length 2,048; learning rate 2e-4; cosine scheduling; 0.03 warmup.
- LoRA rank 16, alpha 32, dropout 0.05, targeting attention projections.
- Recorded training runtime: 245.96 seconds; final recorded loss: 0.3542.

Exact historical configuration and library versions are preserved in
[`run_meta.json`](run_meta.json), with aggregate training measurements in
[`train_metrics.json`](train_metrics.json). Historical absolute paths inside
those machine-readable provenance files record the original Colab environment.

## Evaluation

The committed 224-record selection evaluation reports exact match 0.7098 and
token F1 0.8204, with no malformed outputs. See the committed
[metrics](../../../results/tennis_from_tiser_experiments/scored/tennis_from_tiser_e3_lr0.0002_bs4_ga4_qwen7b_20260616_093822/metrics.json)
and the full [adapter comparison](../../../results/tennis_from_tiser_experiments/comparisons/adapter_comparison.md).

## Limitations

- This was one candidate in a sweep evaluated on the same selection set; it is
  not a final-holdout estimate.
- The training data contain model-judge-flagged semantic and trace issues.
- Historical UI model snapshots and decoding settings are unavailable.
- The run used one seed, so training variability is unknown.

## Usage

```bash
python scripts/tennis/evaluate_tennis.py \
  --config config/config_tennis_7b_reported_best.yaml \
  --test-file data/tennis/tennis_test.json \
  --adapter-dir model/tennis_from_tiser_qwen7b_20260616_093822/adapter \
  --condition tennis_from_tiser_qwen7b_20260616_093822_reproduced \
  --prompt-style tiser \
  --output-dir outputs/reproduced/tennis_7b/three_epoch_candidate
```

The base model must be obtained separately and used under its own license and
terms. No separate license is declared for the adapter weights. Repository
software and documentation are covered by [`LICENSE`](../../../LICENSE); the
training dataset is CC BY 4.0 subject to
[`data/tennis/DATASET_LICENSE.md`](../../../data/tennis/DATASET_LICENSE.md).

## Recorded framework versions

- PyTorch 2.11.0+cu128
- Transformers 4.46.3
- PEFT 0.13.2
- TRL 0.12.2
