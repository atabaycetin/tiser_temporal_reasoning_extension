"""M5 - execute a run-matrix cell (GPU).

Generates one deterministic 4-tag trace per run-input prompt for a (model, style) cell:

  model  - a tag in conflict.run.models ('tiser' -> LoRA adapter, 'base' -> off-the-shelf)
  style  - 'tiser' (4-tag) or 'standard' (plain), the M4 run-input file consumed

Greedy decoding (single trace, temperature=None), max_new_tokens from cfg.eval (>=768 for the
full 4-tag trace). Reuses the validated vLLM engine (load_vllm/vllm_generate) with the
byte-identical chat-template wrap; an 'hf' engine fallback mirrors M1. The GPT-4o cell is
external (API) and out of scope here.

Run the star cell first (--model tiser --style tiser), then the surrounding cells.

Output: 'outputs/conflict/generations/<model>__<style>.jsonl' rows {id, conflict_type,
raw_generation} (+ 'run_meta.json'). Join key (id, conflict_type) ties back to M3/M6.
"""

from __future__ import annotations

import gc
import os

from src.conflict.io import read_jsonl, stage_dir, write_jsonl, write_run_meta
from src.utils.config import REPO_ROOT
from src.utils.seeding import set_seed


def _resolve(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def _free(obj) -> None:
    del obj
    gc.collect()
    try:
        import torch

        torch.cuda.empty_cache()
    except Exception:
        pass


def _build_generate(cfg, entry):
    """Return (greedy_generate_fn, cleanup_fn) for the configured engine, driven by
    conflict.run. The fn takes a prompt list and returns one greedy completion each."""
    run_cfg = cfg.conflict.run
    engine = run_cfg.get("engine", "vllm")
    adapter = entry.get("adapter_dir")
    adapter = _resolve(adapter) if adapter else None

    if engine == "vllm":
        from src.inference.vllm_engine import load_vllm, vllm_generate

        llm, tokenizer, lora_request = load_vllm(cfg, adapter, engine_cfg=run_cfg)

        def generate(prompts):
            return vllm_generate(llm, tokenizer, prompts, cfg.eval, lora_request=lora_request)

        return generate, lambda: _free(llm)

    if engine != "hf":
        raise ValueError(f"unknown inference engine {engine!r} (expected 'hf' or 'vllm')")

    from src.inference.generate import generate_batch
    from src.model.loader import load_adapter_for_inference, load_base_for_inference

    model, tokenizer = (
        load_adapter_for_inference(cfg, adapter) if adapter else load_base_for_inference(cfg)
    )

    def generate(prompts):
        return generate_batch(model, tokenizer, prompts, cfg.eval)

    return generate, lambda: _free(model)


def run_inference(cfg, model_tag: str, style: str, limit: int | None = None) -> dict:
    set_seed(cfg.seed)

    entries = {e["tag"]: e for e in cfg.conflict.run.models}
    if model_tag not in entries:
        raise ValueError(f"no model entry for tag {model_tag!r} (have {sorted(entries)})")

    in_path = os.path.join(stage_dir(cfg, "run_inputs"), f"{style}.jsonl")
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"missing run inputs for style {style!r}: {in_path} (run M4 first)")
    rows = read_jsonl(in_path)
    if limit is not None:
        rows = rows[:limit]

    generate, cleanup = _build_generate(cfg, entries[model_tag])
    completions = generate([r["prompt"] for r in rows])
    cleanup()

    out_rows = [
        {"id": r["id"], "conflict_type": r["conflict_type"], "raw_generation": gen}
        for r, gen in zip(rows, completions)
    ]
    out_dir = stage_dir(cfg, "generations")
    out_path = os.path.join(out_dir, f"{model_tag}__{style}.jsonl")
    write_jsonl(out_path, out_rows)
    write_run_meta(out_dir, cfg, extra={
        "model_tag": model_tag, "style": style, "n": len(out_rows),
        "engine": cfg.conflict.run.get("engine", "vllm"), "decoding": "greedy",
    })

    print(f"[M5:{model_tag}__{style}] generated {len(out_rows)} traces -> {out_path}")
    return {"model_tag": model_tag, "style": style, "n": len(out_rows), "out_path": out_path}
