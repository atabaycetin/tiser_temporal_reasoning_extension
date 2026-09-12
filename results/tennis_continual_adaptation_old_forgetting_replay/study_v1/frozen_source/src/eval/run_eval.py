from __future__ import annotations

import os
from pathlib import Path

from src.experiment.artifacts import append, now
from src.experiment.evaluation import EvaluationStore, evaluation_spec

from src.data.dataset import load_tiser_test
from src.eval.metrics import aggregate, exact_match, token_f1
from src.inference.parser import parse_answer
from src.utils.config import REPO_ROOT
from src.utils.io import ensure_dir, write_json, write_run_meta
from src.utils.seeding import set_seed


def _default_adapter_dir(cfg) -> str:
    return os.path.join(cfg.paths.model_dir, cfg.run_name, "adapter")


def _build_generate(cfg, adapter_dir: str):
    """Return a greedy generate(prompts) -> list[str] for the configured engine.

    `eval.engine` selects the backend; it defaults to 'hf' so the frozen-baseline
    reproduction stays byte-identical. 'vllm' reuses the validated conflict-pipeline
    engine (same chat-template wrap + token-id feed -> identical model inputs), giving
    ~10-50x throughput on the full test set. Greedy in both cases (temperature unset).
    """
    engine = cfg.eval.get("engine", "hf")
    if engine == "vllm":
        from src.inference.vllm_engine import load_vllm, vllm_generate

        abs_adapter = adapter_dir if os.path.isabs(adapter_dir) else os.path.join(REPO_ROOT, adapter_dir)
        llm, tokenizer, lora_request = load_vllm(cfg, abs_adapter, engine_cfg=cfg.eval)
        return lambda prompts: vllm_generate(llm, tokenizer, prompts, cfg.eval, lora_request=lora_request)

    if engine != "hf":
        raise ValueError(f"unknown eval engine {engine!r} (expected 'hf' or 'vllm')")

    from src.inference.generate import generate_batch
    from src.model.loader import load_adapter_for_inference

    model, tokenizer = load_adapter_for_inference(cfg, adapter_dir)
    return lambda prompts: generate_batch(model, tokenizer, prompts, cfg.eval)


def run_eval(cfg, adapter_dir: str | None = None, *, resume=False, manifest=None) -> dict:
    set_seed(cfg.seed)
    adapter_dir = adapter_dir or _default_adapter_dir(cfg)
    run_dir = os.path.join(cfg.paths.output_dir, cfg.run_name)
    test_ds = load_tiser_test(cfg.paths.test_file, cfg.eval.max_samples_per_split)
    _warn_on_unexpected_splits([r["dataset_name"] for r in test_ds], cfg.splits)
    if cfg.eval.get("require_complete_splits", False) and set(cfg.splits) - {r["dataset_name"] for r in test_ds}:
        raise ValueError("Required macro split absent from evaluation population")
    prompts = [r["prompt"] for r in test_ds]
    spec = evaluation_spec(test_ds, prompts, cfg, adapter_dir, input_file=cfg.paths.test_file)
    store = EvaluationStore(run_dir, spec, resume=resume, manifest=manifest)
    append(Path(run_dir) / "execution_attempts.jsonl", {"started_at": now(), "resume": bool(resume),
                                                        "completed_before_attempt": len(store.rows)})
    if not (Path(run_dir) / "run_meta.json").exists():
        write_run_meta(run_dir, cfg)
    generate = _build_generate(cfg, adapter_dir) if len(store.rows) < len(test_ds) else None
    checkpoint_rows = int(cfg.eval.get("checkpoint_rows", 64))
    if checkpoint_rows < cfg.eval.batch_size:
        raise ValueError("Evaluation checkpoint_rows must be at least batch_size")
    pending = []
    for start in range(len(store.rows), len(test_ds), cfg.eval.batch_size):
        rows = test_ds[start:start + cfg.eval.batch_size]
        generations = generate(prompts[start:start + len(rows)])
        if len(generations) != len(rows):
            raise ValueError("Generation count differs from evaluation inputs")
        pending.extend(_score_row(row, raw) for row, raw in zip(rows, generations))
        if len(pending) >= checkpoint_rows or start + len(rows) == len(test_ds):
            store.add(pending)
            pending = []
    records = store.finish()
    metrics = aggregate(records, cfg.splits)
    metrics["n_malformed"] = sum(int(r["malformed"]) for r in records)
    metrics["config_name"] = cfg.run_name
    metrics["adapter_dir"] = adapter_dir
    write_json(os.path.join(run_dir, "metrics.json"), metrics)
    append(Path(run_dir) / "execution_attempts.jsonl", {"completed_at": now(), "status": "complete",
                                                        "completed_records": len(records)})
    print(f"[eval] macro-EM {metrics['macro_em']:.3f} / macro-F1 {metrics['macro_f1']:.3f}")
    print(f"[eval] malformed outputs: {metrics['n_malformed']}/{metrics['n_total']}")
    return metrics


def _score_row(row, raw):
    parsed = parse_answer(raw)
    return {
        "question_id": row["question_id"],
        "dataset_name": row["dataset_name"],
        "gold": row["answer"],
        "raw_generation": raw,
        "pred_answer": parsed.answer,
        "malformed": parsed.malformed,
        "em": exact_match(parsed.answer, row["answer"]),
        "f1": token_f1(parsed.answer, row["answer"]),
    }


def _warn_on_unexpected_splits(names, expected: list[str]) -> None:
    found = set(names)
    unexpected = found - set(expected)
    missing = set(expected) - found
    if unexpected:
        print(f"[eval] WARNING: dataset_name values not in config splits: {sorted(unexpected)}")
    if missing:
        print(f"[eval] WARNING: expected splits absent from test data: {sorted(missing)}")


def _write_predictions(path: str, records: list[dict]) -> None:
    import json

    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
