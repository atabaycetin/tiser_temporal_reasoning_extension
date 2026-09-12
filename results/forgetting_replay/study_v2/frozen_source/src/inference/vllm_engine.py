"""vLLM-backed generation, drop-in for 'generate_batch'.

vLLM ('paged attention') schedules many sequences through the GPU without padding
waste, giving ~10-50x the throughput of HF 'model.generate' on the same model and
weights. Used by the conflict pipeline's GPU stages (M1 memory elicitation, later
the M5 run matrix) where HF generation is the bottleneck.

Fidelity contract (must match 'src.inference.generate.generate_batch'):
  * the prompt is wrapped in the SAME chat template used at training
    ('apply_chat_template(..., add_generation_prompt=True)'), then tokenized with
    'add_special_tokens=False' (the template already carries them) and fed to vLLM
    as explicit token ids -- so the model sees byte-identical input to the HF path;
  * greedy when 'temperature is None' (temperature=0.0), else sampling at the given
    temperature/top_p;
  * 'num_return_sequences=k' returns the k samples for prompt *i* as the contiguous
    block 'out[i*k : (i+1)*k]', in input order -- identical to generate_batch, so the
    self-consistency slicing in M1 is engine-agnostic.

GPU-only; 'vllm' is an optional dependency (see requirements.txt). Imported lazily.
"""

from __future__ import annotations

import os

from transformers import AutoTokenizer


def load_vllm(cfg, adapter_dir: str | None, *, engine_cfg=None):
    """Load a vLLM engine for the base model, optionally with a LoRA adapter.

    Returns (llm, tokenizer, lora_request); 'lora_request' is None for the base model.
    'adapter_dir' must already be an absolute path (the caller resolves it).

    'engine_cfg' supplies the vLLM knobs (gpu_memory_utilization, max_model_len); it
    defaults to 'cfg.conflict.memory' (M1) but M5 passes 'cfg.conflict.run'.
    """
    # bf16 inference does not use FP8 kernels; recent vLLM otherwise probes DeepGEMM
    # at warmup and hard-fails if the (FP8-only) 'deep_gemm' lib is absent. Set before
    # importing vllm so the engine-core subprocess inherits it. 'setdefault' lets an
    # explicit env override win.
    os.environ.setdefault("VLLM_USE_DEEP_GEMM", "0")

    from vllm import LLM
    from vllm.lora.request import LoRARequest

    mem_cfg = engine_cfg if engine_cfg is not None else cfg.conflict.memory
    tokenizer = AutoTokenizer.from_pretrained(cfg.model.name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    enable_lora = adapter_dir is not None
    llm_kwargs = dict(
        model=cfg.model.name,
        dtype="bfloat16",  # match the bf16 baseline (config load_in_4bit: false)
        seed=cfg.seed,
        gpu_memory_utilization=mem_cfg.get("gpu_memory_utilization", 0.90),
        enable_lora=enable_lora,
    )
    if enable_lora:
        # vLLM needs the max rank up front; the adapter rank is config.lora.r.
        llm_kwargs["max_lora_rank"] = cfg.lora.r
    max_model_len = mem_cfg.get("max_model_len", None)
    if max_model_len is not None:
        llm_kwargs["max_model_len"] = max_model_len

    llm = LLM(**llm_kwargs)
    # adapter id 1: a single adapter is loaded per process (M1 runs one model entry
    # per invocation when using --only-model, the recommended vLLM workflow).
    lora_request = LoRARequest("adapter", 1, adapter_dir) if enable_lora else None
    return llm, tokenizer, lora_request


def _engine_max_len(llm, gen_cfg) -> int:
    """Resolve the engine's context cap (tokens). Prefer an explicit 'max_model_len' in
    'gen_cfg', else read it off the live engine, else fall back to Qwen2.5's 32768."""
    cap = gen_cfg.get("max_model_len", None) if hasattr(gen_cfg, "get") else getattr(gen_cfg, "max_model_len", None)
    if cap:
        return int(cap)
    for attr in ("llm_engine", "engine"):
        mc = getattr(getattr(llm, attr, None), "model_config", None)
        if mc is not None and getattr(mc, "max_model_len", None):
            return int(mc.max_model_len)
    return 32768


def vllm_generate(
    llm,
    tokenizer,
    prompts: list[str],
    gen_cfg,
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    num_return_sequences: int = 1,
    lora_request=None,
) -> list[str]:
    """vLLM generation matching generate_batch's signature and flat-output contract."""
    from vllm import SamplingParams

    # A prompt longer than (context - max_new_tokens) is unservable: vLLM raises
    # VLLMValidationError and tears down the WHOLE batch (not just that request). The
    # full TISER test set has a handful of such items (only the OOD tot_semantic split;
    # in-domain prompts are <2k tokens), so skip them and emit an empty completion in
    # their slot -- scored as malformed/EM=0, honest since the model can't ingest them.
    # No-op for normal prompts, so the conflict-pipeline (M1/M5) output is unchanged.
    budget = _engine_max_len(llm, gen_cfg) - gen_cfg.max_new_tokens

    # Pass token ids as the stable dict form ('{"prompt_token_ids": ids}'), accepted by
    # llm.generate on vLLM >= 0.6 -- avoids the churn in the TokensPrompt import path.
    token_prompts = []
    keep_idx: list[int] = []  # original index of each kept prompt, for output alignment
    n_skipped = 0
    for i, p in enumerate(prompts):
        text = tokenizer.apply_chat_template(
            [{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True
        )
        ids = tokenizer(text, add_special_tokens=False)["input_ids"]
        if len(ids) > budget:
            n_skipped += 1
            continue
        token_prompts.append({"prompt_token_ids": ids})
        keep_idx.append(i)
    if n_skipped:
        print(f"[vllm] skipping {n_skipped}/{len(prompts)} prompt(s) over the "
              f"{budget}-token budget; emitting empty completion for those slots")

    sampling = temperature is not None
    # Reproducibility comes from the engine-level seed (LLM(seed=cfg.seed)); no
    # per-request seed (with n>1 that would just reseed the same diverse draw).
    sp = SamplingParams(
        n=num_return_sequences,
        temperature=temperature if sampling else 0.0,
        top_p=top_p if (sampling and top_p is not None) else 1.0,
        max_tokens=gen_cfg.max_new_tokens,
    )

    # vLLM returns RequestOutputs in input order; each carries 'n' CompletionOutputs
    # in sample order -> flatten to the i*k block layout generate_batch produces.
    # Skipped prompts keep their i*k slot as "" so the output stays aligned with input.
    k = num_return_sequences
    flat: list[str] = [""] * (len(prompts) * k)
    req_outputs = llm.generate(token_prompts, sp, lora_request=lora_request) if token_prompts else []
    for src_i, ro in zip(keep_idx, req_outputs):
        for j, comp in enumerate(ro.outputs):
            flat[src_i * k + j] = comp.text
    return flat
