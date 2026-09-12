"""Shared IO helpers for the conflict pipeline.

Every stage writes a versioned artifact + 'run_meta.json' under
'outputs/conflict/<stage>/' (the project's asset-backed-provenance rule).
"""

from __future__ import annotations

import datetime
import json
import os

from src.utils.io import ensure_dir, git_sha, write_json

# Library versions worth pinning when present. Imported best-effort so the CPU
# stages (M0/M2) run on a laptop without the GPU stack installed.
_TRACKED_LIBS = ("torch", "transformers", "peft", "trl", "datasets", "vllm")


def stage_dir(cfg, stage: str) -> str:
    """'outputs/conflict/<stage>/' (created)."""
    path = os.path.join(cfg.paths.output_dir, "conflict", stage)
    ensure_dir(path)
    return path


def _library_versions() -> dict:
    versions = {}
    for name in _TRACKED_LIBS:
        try:
            versions[name] = __import__(name).__version__
        except Exception:
            versions[name] = None
    return versions


def write_run_meta(out_dir: str, cfg, extra: dict | None = None) -> None:
    """Stage provenance: timestamp, git SHA, best-effort lib versions, config (+ extra).

    Like 'src.utils.io.write_run_meta' but tolerates a missing GPU stack so M0/M2
    write a meta on CPU; on the GPU box (M1) the real versions are captured.
    """
    meta = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "library_versions": _library_versions(),
        "config": cfg,
    }
    if extra:
        meta.update(extra)
    write_json(os.path.join(out_dir, "run_meta.json"), meta)


def write_jsonl(path: str, rows: list[dict]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def read_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_records(path: str) -> list[dict]:
    """Load a TISER data file (JSON array, or JSONL fallback).

    Mirrors 'src.data.dataset._load_records' but lives here so the CPU stages
    (M0/M2) don't import that module, which pulls in HF 'datasets' (GPU-stack only).
    """
    with open(path) as f:
        try:
            obj = json.load(f)
        except json.JSONDecodeError:
            f.seek(0)
            return [json.loads(line) for line in f if line.strip()]
    if not isinstance(obj, list):
        raise ValueError(f"{path}: expected a JSON array of records, got {type(obj).__name__}")
    return obj
