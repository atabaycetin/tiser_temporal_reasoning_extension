---
base_model: Qwen/Qwen2.5-7B-Instruct
library_name: peft
---

# TISER Qwen2.5-7B LoRA Adapter

This PEFT LoRA adapter is the repository's reproduced TISER baseline for
structured temporal reasoning. It generates a reasoning trace with timeline,
reflection, and answer sections; downstream scoring extracts the final answer.

## Intended use

Use this adapter with `Qwen/Qwen2.5-7B-Instruct` to reproduce the baseline,
run the context-memory conflict probe, or initialize the documented tennis
continued-adaptation experiments. It is a research artifact, not a general
factual, medical, legal, or safety-critical assistant.

## Training

- Training data: the full TISER training release in `data/TISER_train.json`.
- Seed: 42.
- Training: three epochs, maximum sequence length 2,048, effective batch size
  16, learning rate 2e-4 with cosine scheduling and 0.03 warmup.
- LoRA: rank 16, alpha 32, dropout 0.05, targeting attention projection layers.
- Precision: bf16 base-model loading; the base model is not included here.

The portable configuration is
[`config/config.yaml`](../../../config/config.yaml). The adapter contains
weights, tokenizer files, and serialized training arguments.

## Evaluation

The committed full evaluation reports macro exact match 0.8778 and macro F1
0.9486 over five in-domain TISER test splits. The 2,800-example ToT-semantic
OOD split is reported separately and excluded from that macro. See
[`results/baseline/tiser_qwen7b_full/metrics.json`](../../../results/baseline/tiser_qwen7b_full/metrics.json)
and the repository [README](../../../README.md#full-reported-baseline).

## Limitations

- Results are tied to the recorded data, prompts, parser, and library/backend
  behavior; regenerated text may differ across environments.
- The adapter can produce malformed traces or unsupported reasoning even when
  its extracted answer is correct.
- Evaluation is benchmark-based and does not establish real-world reliability.
- The original training run represents one seed, so training variability is
  not measured.

## Usage

Run the documented evaluator from the repository root:

```bash
python scripts/evaluate.py \
  --config config/config.yaml \
  --adapter-dir model/tiser_qwen7b_full/adapter \
  --eval-engine hf
```

The base model must be obtained separately and used under its own license and
terms. No separate license is declared for the adapter weights. Repository
software and documentation are covered by [`LICENSE`](../../../LICENSE); the
tennis dataset has separate terms documented in
[`data/tennis/DATASET_LICENSE.md`](../../../data/tennis/DATASET_LICENSE.md).

## Framework

- PEFT 0.13.2
