from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import os
from pathlib import Path
from collections import Counter

import torch
from transformers import DataCollatorForSeq2Seq, TrainerCallback
from torch.utils.data import DataLoader
from trl import SFTConfig, SFTTrainer

from src.data.dataset import build_train_dataset
from src.model.loader import build_lora_config, load_model_and_tokenizer
from src.utils.io import read_json, write_json, write_run_meta
from src.utils.seeding import set_seed
from src.experiment.artifacts import append, digest, freeze, now, read, sha256, source_snapshot, tree_hash, write
from src.experiment.evaluation import environment, hardware
from src.train.exposure import Exposure, planned_exposure, schedule_batches


class FixedBatchSampler:
    def __init__(self, n, batch_size, count, seed):
        self.n, self.batch_size, self.count, self.seed = n, batch_size, count, seed
        self.drop_last = True

    def __len__(self):
        return self.count

    def __iter__(self):
        return schedule_batches(self.n, self.batch_size, self.count, self.seed)


class ExposureCallback(TrainerCallback):
    def __init__(self, trainer):
        self.trainer = trainer

    def on_step_end(self, args, state, control, **kwargs):
        self.trainer.exposure.update(state.global_step)

    def on_save(self, args, state, control, **kwargs):
        path = Path(args.output_dir) / f"checkpoint-{state.global_step}"
        write(path / "token_exposure.json", self.trainer.exposure.to_dict())
        write(path / "training_spec.json", self.trainer.training_spec)


class MeasuredSFTTrainer(SFTTrainer):
    def __init__(self, *args, fixed_schedule=False, **kwargs):
        self.fixed_schedule = fixed_schedule
        self.exposure = Exposure()
        self.training_spec = {}
        super().__init__(*args, **kwargs)
        self.add_callback(ExposureCallback(self))

    def get_train_dataloader(self):
        if not self.fixed_schedule:
            return super().get_train_dataloader()
        if self.args.world_size != 1:
            raise ValueError("The preregistered fixed schedule requires one GPU")
        sampler = FixedBatchSampler(len(self.train_dataset), self.args.per_device_train_batch_size,
                                    self.args.max_steps * self.args.gradient_accumulation_steps, self.args.seed)
        # A private loader generator prevents iterator construction from consuming
        # the model's RNG stream on a resumed run.
        generator = torch.Generator().manual_seed(self.args.seed)
        return self.accelerator.prepare(DataLoader(self.train_dataset, batch_sampler=sampler,
                                                  collate_fn=self.data_collator, generator=generator))

    def training_step(self, model, inputs, *args, **kwargs):
        loss = super().training_step(model, inputs, *args, **kwargs)
        self.exposure.observe(inputs["attention_mask"].sum(dim=1).detach().cpu().tolist(),
                              (inputs["labels"][:, 1:] != -100).sum(dim=1).detach().cpu().tolist())
        return loss


def _sft_config(cfg) -> SFTConfig:
    use_bf16 = torch.cuda.is_bf16_supported()
    return SFTConfig(
        output_dir=os.path.join(cfg.paths.output_dir, cfg.run_name, "trainer"),
        per_device_train_batch_size=cfg.train.per_device_batch_size,
        gradient_accumulation_steps=cfg.train.gradient_accumulation_steps,
        num_train_epochs=cfg.train.num_epochs,
        max_steps=cfg.train.get("max_steps", -1),
        learning_rate=cfg.train.learning_rate,
        lr_scheduler_type=cfg.train.lr_scheduler_type,
        warmup_ratio=cfg.train.warmup_ratio,
        weight_decay=cfg.train.weight_decay,
        optim=cfg.train.optim,
        max_seq_length=cfg.train.max_seq_len,
        gradient_checkpointing=cfg.train.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=use_bf16,
        fp16=not use_bf16,
        logging_steps=cfg.train.logging_steps,
        save_strategy=cfg.train.save_strategy,
        save_steps=cfg.train.get("save_steps", 25),
        seed=cfg.seed,
        # packing would concatenate examples and break per-example completion-only masking.
        packing=False,
        report_to=[],
    )


def build_trainer(cfg, model, tokenizer, train_ds) -> SFTTrainer:
    # train_ds is already tokenized (input_ids/attention_mask/labels), so SFTTrainer
    # skips its own prep and does NOT apply the chat template a second time. The
    # seq2seq collator pads input_ids and the -100 labels (so completion-only
    # masking is preserved) -- the default LM collator would overwrite labels.
    collator = DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100)
    kwargs = {
        "model": model,
        "args": _sft_config(cfg),
        "train_dataset": train_ds,
        "processing_class": tokenizer,
        "data_collator": collator,
    }
    # If training starts from an existing PEFT adapter, it is already attached
    # as trainable. Passing a fresh peft_config would create a second adapter.
    if not getattr(model, "peft_config", None):
        kwargs["peft_config"] = build_lora_config(cfg)
    return MeasuredSFTTrainer(**kwargs, fixed_schedule=cfg.train.get("fixed_schedule", False))


def _json_safe(obj):
    return json.loads(json.dumps(obj, default=str))


def _trainer_state_dict(trainer: SFTTrainer) -> dict:
    state = trainer.state
    if hasattr(state, "to_json_string"):
        return json.loads(state.to_json_string())
    if hasattr(state, "to_dict"):
        return _json_safe(state.to_dict())
    if is_dataclass(state):
        return _json_safe(asdict(state))
    return _json_safe(vars(state))


def _save_training_artifacts(
    trainer: SFTTrainer,
    train_metrics: dict,
    *,
    run_dir: str,
    adapter_dir: str,
) -> None:
    trainer_state = _trainer_state_dict(trainer)
    log_history = trainer_state.get("log_history", [])
    run_meta = read_json(os.path.join(run_dir, "run_meta.json"))

    for target_dir in (run_dir, adapter_dir):
        write_json(os.path.join(target_dir, "train_metrics.json"), train_metrics)
        write_json(os.path.join(target_dir, "train_log_history.json"), log_history)
        write_json(os.path.join(target_dir, "trainer_state.json"), trainer_state)
        write_json(os.path.join(target_dir, "run_meta.json"), run_meta)


def run_training(cfg) -> str:
    set_seed(cfg.seed)
    run_dir = os.path.join(cfg.paths.output_dir, cfg.run_name)
    adapter_dir = os.path.join(cfg.paths.model_dir, cfg.run_name, "adapter")
    resume = cfg.train.get("resume_from_checkpoint")
    if (Path(adapter_dir).exists() or (Path(run_dir).exists() and any(Path(run_dir).iterdir()))) and not resume:
        raise FileExistsError("Training output exists; choose a new run name or resume a full checkpoint")
    spec_cfg = json.loads(json.dumps(cfg))
    spec_cfg["train"].pop("resume_from_checkpoint", None)
    spec = {"config": spec_cfg, "train_sha256": sha256(cfg.paths.train_file),
            "starting_adapter": tree_hash(cfg.model.base_adapter) if cfg.model.get("base_adapter") else None,
            "source_sha256": source_snapshot()["sha256"], "environment": environment(), "hardware": hardware()}
    freeze(Path(run_dir) / "training_spec.json", spec)
    restored = None
    if resume:
        checkpoint = Path(resume)
        for name in ("optimizer.pt", "scheduler.pt", "rng_state.pth", "trainer_state.json", "token_exposure.json", "training_spec.json"):
            if not (checkpoint / name).is_file():
                raise ValueError(f"Incomplete resume checkpoint: missing {name}")
        if read(checkpoint / "training_spec.json") != spec:
            raise ValueError("Resume checkpoint differs from frozen training inputs")
        restored = Exposure.restore(read(checkpoint / "token_exposure.json"), read(checkpoint / "trainer_state.json")["global_step"])
    append(Path(run_dir) / "execution_attempts.jsonl", {"started_at": now(), "resume_checkpoint": str(resume) if resume else None,
                                                        "restored_optimizer_step": restored.to_dict()["optimizer_steps"] if restored else 0})
    if not (Path(run_dir) / "run_meta.json").exists():
        write_run_meta(run_dir, cfg)

    model, tokenizer = load_model_and_tokenizer(cfg)

    train_ds, n_dropped, metadata = build_train_dataset(
        cfg.paths.train_file, tokenizer, cfg.train.max_seq_len, cfg.train.subset_size, return_metadata=True
    )
    if not len(train_ds):
        raise ValueError("No training rows survived filtering")
    if cfg.train.get("expected_train_count") is not None and len(train_ds) != cfg.train.expected_train_count:
        raise ValueError("Post-filter training count differs from preregistered condition")
    freeze(Path(run_dir) / "training_population.json", metadata)
    meta = read(Path(run_dir) / "run_meta.json")
    meta.update({"training_spec_sha256": digest(spec), "gpu": torch.cuda.get_device_name() if torch.cuda.is_available() else None,
                 "base_model_revision": getattr(model.config, "_commit_hash", None),
                 "tokenizer_revision": tokenizer.init_kwargs.get("_commit_hash"),
                 "training_counts_by_source": dict(Counter(r["replay_source"] for r in metadata["accepted"]))})
    write(Path(run_dir) / "run_meta.json", meta)
    print(
        f"[train] {len(train_ds)} examples after length filter "
        f"(dropped {n_dropped} > {cfg.train.max_seq_len} tokens)"
    )

    trainer = build_trainer(cfg, model, tokenizer, train_ds)
    trainer.training_spec = spec
    if restored:
        trainer.exposure = restored
    train_result = trainer.train(resume_from_checkpoint=resume)
    train_metrics = dict(train_result.metrics)
    train_metrics["train_examples_after_filter"] = len(train_ds)
    train_metrics["dropped_long_examples"] = n_dropped
    train_metrics["max_seq_len"] = cfg.train.max_seq_len

    exposure = trainer.exposure.to_dict()
    if cfg.train.get("fixed_schedule", False):
        planned = planned_exposure(metadata["accepted"], cfg.train.max_steps, cfg.train.per_device_batch_size,
                                   cfg.train.gradient_accumulation_steps, cfg.seed)
        if exposure != planned:
            raise ValueError("Actual training exposure differs from the deterministic schedule")
    train_metrics["token_exposure"] = exposure
    write(Path(run_dir) / "token_exposure.json", exposure)
    trainer.save_model(adapter_dir)
    write(Path(adapter_dir) / "token_exposure.json", exposure)
    write(Path(adapter_dir) / "training_spec.json", spec)
    _save_training_artifacts(
        trainer,
        train_metrics,
        run_dir=run_dir,
        adapter_dir=adapter_dir,
    )
    append(Path(run_dir) / "execution_attempts.jsonl", {"completed_at": now(), "status": "complete",
                                                        "optimizer_steps": exposure["optimizer_steps"]})
    print(f"[train] saved LoRA adapter to {adapter_dir}")
    print(f"[train] saved training metrics to {os.path.join(adapter_dir, 'train_metrics.json')}")
    return adapter_dir
