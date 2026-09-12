from __future__ import annotations

import json

# HF datasets is needed only by the training path (build_train_dataset's .map/.filter).
# It is imported lazily there so the inference/eval path (and any CPU box without the
# GPU stack) can load the test set without pulling it in.

TRAIN_KEYS = ("dataset_name", "question_id", "question", "answer", "prompt", "output")
TEST_KEYS = ("dataset_name", "question_id", "question", "prompt", "answer")


def _load_records(path: str) -> list[dict]:
    # Released files are a single JSON array; fall back to JSONL if that ever changes.
    with open(path) as f:
        try:
            obj = json.load(f)
        except json.JSONDecodeError:
            f.seek(0)
            return [json.loads(line) for line in f if line.strip()]
    if not isinstance(obj, list):
        raise ValueError(f"{path}: expected a JSON array of records, got {type(obj).__name__}")
    return obj


def _encode_train_example(prompt: str, completion: str, tokenizer) -> dict:
    """Pre-tokenize one example with completion-only label masking.

    Construct the exact chat-templated text expected by an instruct model
    (<|im_start|>user ... <|im_start|>assistant {completion}<|im_end|>) and mask
    everything up to the assistant header so the loss is computed on the gold
    trace only. The trailing EOS stays unmasked so the model learns to stop.
    Tokenizing the dataset ourselves bypasses TRL's automatic prompt/completion
    handling, which would otherwise re-wrap with the chat template and train on
    the whole sequence with no masking.
    """
    full_text = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}, {"role": "assistant", "content": completion}],
        tokenize=False,
    )
    prefix_text = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
    )
    full_ids = tokenizer(full_text, add_special_tokens=False)["input_ids"]
    prefix_ids = tokenizer(prefix_text, add_special_tokens=False)["input_ids"]

    # Mask the longest shared prefix (user turn + assistant header). Matching by
    # token id is robust to any merge at the prefix/completion boundary.
    n_mask = 0
    for a, b in zip(prefix_ids, full_ids):
        if a != b:
            break
        n_mask += 1
    labels = [-100] * n_mask + full_ids[n_mask:]
    return {
        "input_ids": full_ids,
        "attention_mask": [1] * len(full_ids),
        "labels": labels,
    }


def build_train_dataset(
    path: str, tokenizer, max_seq_len: int, subset_size: int | None = None, *, return_metadata=False
) -> tuple[Dataset, int]:
    """Load -> chat-template + completion-only mask -> length filter.

    Inference must wrap prompts with the same chat template (see
    src/inference/generate.py) so the model sees the context it was trained in.
    """
    from datasets import Dataset

    records = _load_records(path)
    if subset_size is not None:
        records = records[:subset_size]
    ds = Dataset.from_list([{"prompt": r["prompt"], "completion": r["output"], "source_index": i} for i, r in enumerate(records)])

    ds = ds.map(
        lambda ex: _encode_train_example(ex["prompt"], ex["completion"], tokenizer),
        remove_columns=["prompt", "completion"],
    )
    before = len(ds)
    ds = ds.filter(lambda ex: len(ex["input_ids"]) <= max_seq_len)
    kept = set(ds["source_index"])
    metadata = {"accepted": [], "rejected": []}
    for row in ds:
        original = records[row["source_index"]]
        metadata["accepted"].append({"question_id": original.get("question_id"),
                                    "dataset_name": original.get("dataset_name"),
                                    "replay_source": original.get("replay_source", "tennis"),
                                    "input_tokens": len(row["input_ids"]),
                                    "supervised_tokens": sum(v != -100 for v in row["labels"][1:])})
    metadata["rejected"] = [{"question_id": r.get("question_id"), "dataset_name": r.get("dataset_name"),
                             "reason": "sequence_length"} for i, r in enumerate(records) if i not in kept]
    ds = ds.remove_columns(["source_index"])
    return (ds, before - len(ds), metadata) if return_metadata else (ds, before - len(ds))


def load_tiser_test(path: str, max_samples_per_split: int | None = None) -> list[dict]:
    """Test records as a plain list of dicts (no datasets dependency).

    run_eval consumes this by row iteration and per-key access, so a list of dicts
    is sufficient and keeps the eval path off the GPU stack.
    """
    records = _load_records(path)
    rows = [{k: r[k] for k in TEST_KEYS} for r in records]
    if max_samples_per_split is not None:
        rows = _cap_per_split(rows, max_samples_per_split)
    return rows


def _cap_per_split(rows: list[dict], n: int) -> list[dict]:
    counts: dict[str, int] = {}
    kept = []
    for row in rows:
        name = row["dataset_name"]
        if counts.get(name, 0) >= n:
            continue
        counts[name] = counts.get(name, 0) + 1
        kept.append(row)
    return kept
