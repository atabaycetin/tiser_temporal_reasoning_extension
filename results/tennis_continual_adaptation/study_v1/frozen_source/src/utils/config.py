from __future__ import annotations

import os

import yaml

# Paths in config.yaml are relative to the repo root; resolve them against it so
# the same file works locally and on Colab regardless of the working directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REQUIRED_TOP_KEYS = ("run_name", "seed", "paths", "model", "lora", "train", "eval", "splits")
_PATH_KEYS = ("data_dir", "train_file", "test_file", "model_dir", "output_dir")


class AttrDict(dict):
    """dict with attribute access (cfg.model.name) that stays JSON-serializable."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


def _wrap(obj):
    if isinstance(obj, dict):
        return AttrDict({k: _wrap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_wrap(v) for v in obj]
    return obj


def load_config(path: str) -> AttrDict:
    with open(path) as f:
        raw = yaml.safe_load(f)

    missing = [k for k in _REQUIRED_TOP_KEYS if k not in raw]
    if missing:
        raise ValueError(f"config {path} is missing required keys: {missing}")

    cfg = _wrap(raw)
    _resolve_paths(cfg)
    return cfg


def _resolve_paths(cfg: AttrDict) -> None:
    for key in _PATH_KEYS:
        cfg.paths[key] = os.path.join(REPO_ROOT, cfg.paths[key])
