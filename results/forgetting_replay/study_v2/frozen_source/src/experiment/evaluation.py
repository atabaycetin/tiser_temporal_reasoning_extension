"""Frozen, chunk-resumable prediction ledger shared by both evaluators."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

from src.experiment.artifacts import digest, freeze, identity, read, sha256, source_snapshot, tree_hash, validate_rows, write


def environment():
    versions = {}
    for name in ("torch", "transformers", "peft", "trl", "accelerate", "bitsandbytes", "numpy"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def hardware():
    """Record the training/evaluation device without making torch a CPU-path import."""
    try:
        import torch
    except ImportError:
        return {"cuda_available": False, "device_count": 0, "devices": []}
    available = torch.cuda.is_available()
    count = torch.cuda.device_count() if available else 0
    devices = []
    for index in range(count):
        devices.append({"name": torch.cuda.get_device_name(index),
                        "capability": list(torch.cuda.get_device_capability(index))})
    return {"cuda_available": available, "device_count": count, "devices": devices}


def evaluation_spec(rows, prompts, cfg, adapter_dir, *, input_file, view=None):
    validate_rows(rows)
    if len(prompts) != len(rows) or any(not isinstance(p, str) or not p.strip() for p in prompts):
        raise ValueError("One non-empty prompt required for every evaluation row")
    if cfg["eval"]["batch_size"] < 1 or cfg["eval"].get("do_sample", False):
        raise ValueError("Resumable study evaluation requires positive batch size and greedy decoding")
    if view:
        validate_tennis_view(view, rows, input_file, gold_key="answer")
    return {"schema_version": 1, "input_sha256": sha256(input_file), "rows_sha256": digest(rows),
            "ordered_ids": [list(identity(r)) for r in rows],
            "ordered_gold": [r["answer"] for r in rows], "prompts_sha256": digest(prompts),
            "config": dict(cfg), "adapter": tree_hash(adapter_dir) if adapter_dir else None,
            "source_sha256": source_snapshot()["sha256"], "environment": environment(), "hardware": hardware(),
            "scoring_view_sha256": sha256(view) if view else None}


class EvaluationStore:
    def __init__(self, output, spec, *, resume=False, manifest=None):
        self.output, self.spec = Path(output), spec
        if manifest:
            expected = read(manifest)
            if expected != spec:
                raise ValueError("Evaluation does not match supplied frozen manifest")
        path = self.output / "evaluation_spec.json"
        if self.output.exists() and any(self.output.iterdir()) and not resume:
            raise FileExistsError(f"Evaluation output exists; use --resume: {self.output}")
        if resume and self.output.exists() and any(self.output.iterdir()) and not path.exists():
            raise ValueError("Cannot resume legacy outputs without an evaluation specification")
        freeze(path, spec)
        self.chunks = self.output / "prediction_chunks"
        self.chunks.mkdir(exist_ok=True)
        self.rows = []
        for path in sorted(self.chunks.glob("*.json")):
            chunk = read(path)
            if chunk["start"] != len(self.rows) or chunk["spec_sha256"] != digest(spec):
                raise ValueError("Missing, reordered or incompatible prediction chunk")
            if chunk["sha256"] != digest(chunk["rows"]):
                raise ValueError("Prediction chunk hash mismatch")
            self._validate(chunk["rows"], len(self.rows))
            self.rows.extend(chunk["rows"])
        self._status()

    def _validate(self, rows, start):
        if not rows or start + len(rows) > len(self.spec["ordered_ids"]):
            raise ValueError("Empty or oversized prediction chunk")
        for index, row in enumerate(rows, start):
            if list(identity(row)) != self.spec["ordered_ids"][index] or row.get("gold") != self.spec["ordered_gold"][index]:
                raise ValueError("Prediction ID/order/gold mismatch")
            if not isinstance(row.get("raw_generation"), str):
                raise ValueError("Missing raw generation")
            if any(k not in row for k in ("em", "f1", "malformed", "pred_answer")):
                raise ValueError("Incomplete prediction row")

    def add(self, rows):
        start = len(self.rows)
        self._validate(rows, start)
        freeze(self.chunks / f"{start:08d}.json", {"start": start, "spec_sha256": digest(self.spec),
                                                "rows": rows, "sha256": digest(rows)})
        self.rows.extend(rows)
        self._status()

    def _status(self):
        write(self.output / "completion.json", {"status": "complete" if len(self.rows) == len(self.spec["ordered_ids"]) else "pending",
              "completed": len(self.rows), "expected": len(self.spec["ordered_ids"]), "spec_sha256": digest(self.spec)})

    def finish(self):
        if len(self.rows) != len(self.spec["ordered_ids"]):
            raise ValueError("Cannot publish an incomplete evaluation")
        write_predictions(self.output / "predictions.jsonl", self.rows)
        self._status()
        return self.rows


def write_predictions(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    tmp.replace(path)


def validate_tennis_view(view_path, rows, input_file, *, gold_key="gold"):
    view = read(view_path)
    if view["sha256"] != digest({k: v for k, v in view.items() if k != "sha256"}):
        raise ValueError("Scoring view was modified after freezing")
    if view["input_sha256"] != sha256(input_file):
        raise ValueError("Scoring view belongs to another input file")
    validate_rows(rows, gold_key)
    entries = view["rows"]
    if [identity(r) for r in entries] != [identity(r) for r in rows]:
        raise ValueError("Scoring view and prediction population differ")
    if any(row[gold_key] != entry["original_gold"] for row, entry in zip(rows, entries)):
        raise ValueError("Original gold differs from audit view")
    if any(type(e.get("eligible")) is not bool or not isinstance(e.get("gold"), str) or not e["gold"].strip() for e in entries):
        raise ValueError("Invalid scoring-view eligibility/gold")
    if sum(e["eligible"] for e in entries) != view["n_primary"] or view["n_primary"] <= 0:
        raise ValueError("Scoring view denominator mismatch or empty population")
    return view


def apply_tennis_view(rows, view_path, input_file):
    from src.tennis.normalize import tennis_exact_match_for_category, tennis_token_f1_for_category
    view = validate_tennis_view(view_path, rows, input_file)
    entries = view["rows"]
    selected = []
    for row, entry in zip(rows, entries):
        if row["gold"] != entry["original_gold"]:
            raise ValueError("Original gold differs from audit view")
        if entry["eligible"]:
            options = {"category": row.get("category"), "tags": row.get("tags", [])}
            gold = entry["gold"]
            selected.append({**row, "original_gold": row["gold"], "gold": gold,
                             "em": tennis_exact_match_for_category(row["pred_answer"], gold, **options),
                             "f1": tennis_token_f1_for_category(row["pred_answer"], gold, **options),
                             "scoring_view_sha256": view["sha256"]})
    if not selected:
        raise ValueError("Audited primary scoring population is empty")
    if len(selected) != view["n_primary"]:
        raise ValueError("Scoring view denominator mismatch")
    return selected
