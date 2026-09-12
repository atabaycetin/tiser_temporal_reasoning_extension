from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

from src.data.dataset import TEST_KEYS, TRAIN_KEYS, _load_records
from src.utils.io import ensure_dir

_MIN_BYTES = 1_000_000  # real files are 208MB / 88MB; LFS pointers are ~130B
_GITHUB_URL = "https://github.com/amazon-science/TISER"
_FILES = ("TISER_train.json", "TISER_test.json")


def _looks_real(path: str) -> bool:
    if not os.path.exists(path) or os.path.getsize(path) < _MIN_BYTES:
        return False
    with open(path, "rb") as f:
        return not f.read(64).startswith(b"version https://git-lfs")


def ensure_data(cfg) -> None:
    ensure_dir(cfg.paths.data_dir)
    targets = {name: os.path.join(cfg.paths.data_dir, name) for name in _FILES}

    if all(_looks_real(p) for p in targets.values()):
        print("[fetch] data already present and valid; skipping download")
    elif _copy_from_local(cfg, targets):
        print(f"[fetch] copied real files from {cfg.paths.local_source_dir}")
    else:
        _fetch_fallback(cfg, targets)

    _validate(targets)


def _copy_from_local(cfg, targets: dict[str, str]) -> bool:
    src_dir = cfg.paths.local_source_dir
    sources = {name: os.path.join(src_dir, name) for name in _FILES}
    if not all(_looks_real(p) for p in sources.values()):
        return False
    for name, dst in targets.items():
        shutil.copyfile(sources[name], dst)
    return True


def _fetch_fallback(cfg, targets: dict[str, str]) -> None:
    if _fetch_from_hub(cfg, targets):
        print(f"[fetch] downloaded from HuggingFace hub: {cfg.paths.hf_dataset_id}")
        return
    _fetch_via_git_lfs(targets)
    print(f"[fetch] cloned via git-lfs from {_GITHUB_URL}")


def _fetch_from_hub(cfg, targets: dict[str, str]) -> bool:
    try:
        from huggingface_hub import snapshot_download

        local = snapshot_download(
            cfg.paths.hf_dataset_id, repo_type="dataset", allow_patterns=["**/*.json"]
        )
    except Exception as exc:  # hub id may be wrong / offline -> fall through to git-lfs
        print(f"[fetch] hub download unavailable ({exc}); trying git-lfs")
        return False

    found = _locate_files(local)
    if set(found) != set(_FILES):
        return False
    for name, dst in targets.items():
        shutil.copyfile(found[name], dst)
    return True


def _fetch_via_git_lfs(targets: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "lfs", "clone", _GITHUB_URL, tmp], check=True)
        found = _locate_files(tmp)
        for name, dst in targets.items():
            shutil.copyfile(found[name], dst)


def _locate_files(root: str) -> dict[str, str]:
    found = {}
    for dirpath, _, filenames in os.walk(root):
        for name in _FILES:
            if name in filenames:
                found[name] = os.path.join(dirpath, name)
    return found


def _validate(targets: dict[str, str]) -> None:
    expected = {"TISER_train.json": TRAIN_KEYS, "TISER_test.json": TEST_KEYS}
    for name, path in targets.items():
        records = _load_records(path)
        missing = set(expected[name]) - set(records[0])
        if missing:
            raise ValueError(f"{name}: records missing expected keys {sorted(missing)}")
        splits = sorted({r["dataset_name"] for r in records})
        print(f"[fetch] {name}: {len(records)} records, splits={splits}")
