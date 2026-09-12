from __future__ import annotations

import torch
from peft import LoraConfig, PeftModel, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedModel,
    PreTrainedTokenizer,
)


def _compute_dtype() -> torch.dtype:
    # A100 -> bf16, T4 -> fp16.
    return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16


def _bnb_config(cfg) -> BitsAndBytesConfig:
    return BitsAndBytesConfig(
        load_in_4bit=cfg.model.load_in_4bit,
        bnb_4bit_quant_type=cfg.model.bnb_4bit_quant_type,
        bnb_4bit_use_double_quant=cfg.model.bnb_4bit_use_double_quant,
        bnb_4bit_compute_dtype=_compute_dtype(),
    )


def _load_tokenizer(name: str, revision=None) -> PreTrainedTokenizer:
    tokenizer = AutoTokenizer.from_pretrained(name, **({"revision": revision} if revision else {}))
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def _load_base(cfg) -> PreTrainedModel:
    """Load the frozen base model.

    'model.load_in_4bit: true' -> QLoRA path (4-bit nf4 base), the smoke-validated
    default. 'false' -> bf16 base (no quantization): faster per step and closer to
    the paper, worth it on an 80GB H100 where the full-precision 7B fits with room.
    """
    if cfg.model.load_in_4bit:
        return AutoModelForCausalLM.from_pretrained(
            cfg.model.name,
            **({"revision": cfg.model.revision} if cfg.model.get("revision") else {}),
            quantization_config=_bnb_config(cfg),
            device_map="auto",
        )
    return AutoModelForCausalLM.from_pretrained(
        cfg.model.name,
        **({"revision": cfg.model.revision} if cfg.model.get("revision") else {}),
        torch_dtype=_compute_dtype(),
        device_map="auto",
    )


def _training_base_adapter(cfg) -> str | None:
    return cfg.model.get("base_adapter") or None


def _prepare_for_training(model: PreTrainedModel, cfg) -> PreTrainedModel:
    if cfg.model.load_in_4bit:
        return prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=cfg.train.gradient_checkpointing
        )
    if cfg.train.gradient_checkpointing:
        # kbit prep normally wires these up; do it by hand on the bf16 path.
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()
    return model


def load_model_and_tokenizer(cfg) -> tuple[PreTrainedModel, PreTrainedTokenizer]:
    tokenizer = _load_tokenizer(cfg.model.name, cfg.model.get("tokenizer_revision", cfg.model.get("revision")))
    tokenizer.padding_side = "right"  # training; generation flips this to "left"

    model = _load_base(cfg)
    model = _prepare_for_training(model, cfg)

    base_adapter = _training_base_adapter(cfg)
    if base_adapter:
        model = PeftModel.from_pretrained(model, base_adapter, is_trainable=True)
    return model, tokenizer


def build_lora_config(cfg) -> LoraConfig:
    return LoraConfig(
        r=cfg.lora.r,
        lora_alpha=cfg.lora.alpha,
        lora_dropout=cfg.lora.dropout,
        target_modules=list(cfg.lora.target_modules),
        bias=cfg.lora.bias,
        task_type="CAUSAL_LM",
    )


def _clear_sampling_defaults(model) -> None:
    # Qwen ships sampling defaults (temperature/top_p/top_k) in its generation
    # config; with greedy decoding they do nothing but spam warnings. Clear them.
    # Per-call sampling kwargs (M1 self-consistency) still override these.
    gen_cfg = model.generation_config
    gen_cfg.do_sample = False
    gen_cfg.temperature = None
    gen_cfg.top_p = None
    gen_cfg.top_k = None


def load_adapter_for_inference(cfg, adapter_dir: str) -> tuple[PeftModel, PreTrainedTokenizer]:
    tokenizer = _load_tokenizer(cfg.model.name, cfg.model.get("tokenizer_revision", cfg.model.get("revision")))
    tokenizer.padding_side = "left"  # left-pad for batched generation

    base = _load_base(cfg)
    model = PeftModel.from_pretrained(base, adapter_dir)
    model.eval()
    _clear_sampling_defaults(model)
    return model, tokenizer


def load_base_for_inference(cfg) -> tuple[PreTrainedModel, PreTrainedTokenizer]:
    """Load the off-the-shelf base model (no adapter) for inference.

    Mirrors 'load_adapter_for_inference' minus the PEFT wrap -- used by M1 to elicit
    the base model's parametric memory as a cross-check on the fine-tuned subject.
    """
    tokenizer = _load_tokenizer(cfg.model.name, cfg.model.get("tokenizer_revision", cfg.model.get("revision")))
    tokenizer.padding_side = "left"

    model = _load_base(cfg)
    model.eval()
    _clear_sampling_defaults(model)
    return model, tokenizer
