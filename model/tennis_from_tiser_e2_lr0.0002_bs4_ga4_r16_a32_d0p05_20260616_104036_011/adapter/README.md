---
base_model: Qwen/Qwen2.5-7B-Instruct
library_name: peft
---

# Selected Tennis-from-TISER Qwen2.5-7B LoRA Adapter

This PEFT LoRA adapter is the selected 7B tennis continued-adaptation artifact.
Training began from the repository's TISER 7B adapter and continued for two
epochs on 600 supervised tennis temporal-reasoning traces.

## Intended use

Use this adapter with `Qwen/Qwen2.5-7B-Instruct` to reproduce the selected
tennis-domain transfer result and the registered retention/final-holdout study.
It is a research artifact, not a factual tennis database or a safety-critical
assistant.

## Training

- Initialization: `model/tiser_qwen7b_full/adapter`.
- Data: all 600 records in `data/tennis/tennis_train_traced_full.json`.
- Seed 42; two epochs; batch size 4 with four accumulation steps; maximum
  sequence length 2,048; learning rate 2e-4; cosine scheduling; 0.03 warmup.
- Base model loading: 4-bit NF4 with double quantization.
- LoRA rank 16, alpha 32, dropout 0.05, targeting attention projections.
- Recorded training runtime: 165.09 seconds; final recorded loss: 0.4170.

Exact historical configuration and library versions are preserved in
[`run_meta.json`](run_meta.json), with aggregate training measurements in
[`train_metrics.json`](train_metrics.json). The portable reconstruction config
is
[`config/config_tennis_7b_reported_best.yaml`](../../../config/config_tennis_7b_reported_best.yaml).
Historical absolute paths inside machine-readable provenance files record the
original Colab environment.

## Evaluation

The original historical 224-record evaluation reports exact match 0.7321 and
token F1 0.8558. The later frozen study reran the unchanged adapter with its
registered prompt and audited scoring view: it reached 0.7277 EM / 0.8522 F1 on
the 224-record selection set and 0.7345 EM / 0.8335 F1 on the separate
113-record final holdout. All three evaluations recorded zero malformed
outputs. See the historical [metrics](../../../results/tennis_from_tiser_experiments/scored/tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011/metrics.json),
the frozen [selection metrics](../../../results/forgetting_replay/study_v2/evaluations/selection/tennis/C1/metrics.json),
and the frozen [final metrics](../../../results/forgetting_replay/study_v2/evaluations/final/tennis/C1/metrics.json).

## Limitations

- Candidate selection used the 224-record set, so the 113-record frozen
  holdout is the appropriate final estimate.
- The synthetic training data contain model-judge-flagged semantic and trace
  issues; their causal effect was not measured.
- The retention gate was inconclusive, establishing neither clear forgetting
  nor non-inferiority under the registered margin.
- The run used one seed, so training variability is unknown.
- Historical UI model snapshots and decoding settings remain unavailable.

## Usage

```bash
python scripts/tennis/evaluate_tennis.py \
  --config config/config_tennis_7b_reported_best.yaml \
  --test-file data/tennis/tennis_test.json \
  --adapter-dir model/tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011/adapter \
  --condition tennis_from_tiser_best_reproduced \
  --prompt-style tiser \
  --output-dir outputs/reproduced/tennis_7b/continued_adaptation
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
