---
base_model: Qwen/Qwen2.5-0.5B-Instruct
library_name: peft
---

# Tennis Temporal-QA Qwen2.5-0.5B LoRA Adapter

This is the exact historical PEFT LoRA adapter used for the reported standalone
0.5B tennis temporal-QA subexperiment. It was recovered from Git commit
`53a135a`; `adapter_model.safetensors` is 8,676,008 bytes with SHA-256
`01e89ffbbc939622cd9213d8150eab2bca4643f954dd26e6154496ed89cae64b`.

## Intended use

Use this adapter with `Qwen/Qwen2.5-0.5B-Instruct` to audit or reproduce the
historical small-model tennis result. It is not the repository's 7B
continued-adaptation result and is not intended for factual tennis lookup or
safety-critical use.

## Training

- Training data: 600 supervised traces from
  `data/tennis/tennis_train_traced_full.json`.
- Reconstructed portable settings: seed 42, one epoch, batch size 1, maximum
  sequence length 2,048, and learning rate 2e-4 with cosine scheduling.
- LoRA: rank 16, alpha 32, dropout 0.05, targeting attention projection layers.
- Base model: `Qwen/Qwen2.5-0.5B-Instruct`, stored separately.

The portable settings in
[`config/config_tennis_0p5b_reported_full600.yaml`](../../../config/config_tennis_0p5b_reported_full600.yaml)
were reconstructed from committed artifacts. They support a new reproduction
but do not fill gaps in the original run's hardware and environment provenance.
The training data are documented in the
[`data/tennis/DATASET_CARD.md`](../../../data/tennis/DATASET_CARD.md).

## Evaluation

On the historical 224-record tennis test, this adapter with TISER prompting
reached exact match 0.4643 and token F1 0.5164, with no malformed outputs. The
standard-prompt base model reached 0.3795 exact match and 0.4717 F1. See the
committed [metrics](../../../results/tennis_domain_adaptation/scored/tennis_only_full600_test224/metrics.json)
and the repository [README](../../../README.md#05b-reported-subexperiment).

## Limitations

- The synthetic dataset contains model-judge-flagged semantic and trace issues;
  consult the dataset card before interpreting the result.
- The historical GPU and complete software environment were not recorded.
- This is a single-seed, small-model subexperiment.
- The adapter is specialized for the repository's prompt and answer parser and
  should not be treated as a general tennis model.

## Usage

```bash
python scripts/tennis/evaluate_tennis.py \
  --config config/config_tennis_0p5b_reported_full600.yaml \
  --test-file data/tennis/tennis_test.json \
  --adapter-dir model/tiser_tennis_full600_smoke/adapter \
  --condition tennis_only_full600_historical_restored \
  --prompt-style tiser \
  --output-dir outputs/reproduced/tennis_0p5b/historical_restored
```

The base model must be obtained separately and used under its own license and
terms. No separate license is declared for the adapter weights. Repository
software and documentation are covered by [`LICENSE`](../../../LICENSE); the
training dataset is CC BY 4.0 subject to
[`data/tennis/DATASET_LICENSE.md`](../../../data/tennis/DATASET_LICENSE.md).

## Framework

- PEFT 0.13.2
