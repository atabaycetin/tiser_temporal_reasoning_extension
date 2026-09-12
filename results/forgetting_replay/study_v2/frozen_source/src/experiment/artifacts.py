"""Small standard-library primitives shared by CPU and GPU workflows."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    """Atomic replacement; callers own the immutable/existing-file policy."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def freeze(path, value):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ValueError(f"Frozen artifact differs: {path}")
    else:
        write(path, value)


def jsonl(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def append(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def identity(row):
    result = tuple(str(row.get(k) or "").strip() for k in ("dataset_name", "question_id"))
    if not all(result):
        raise ValueError("Every record requires non-empty dataset_name and question_id")
    return result


def validate_rows(rows, gold_key="answer"):
    if not rows:
        raise ValueError("Empty population")
    ids = [identity(r) for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate stable IDs")
    for row in rows:
        if not isinstance(row.get(gold_key), str) or not row[gold_key].strip():
            raise ValueError(f"Missing non-empty {gold_key}: {identity(row)}")
    return ids


def file_hashes(paths):
    return {str(Path(p)): sha256(p) for p in paths}


def tree_hash(path):
    path = Path(path)
    if not path.is_dir():
        raise FileNotFoundError(path)
    files = {p.relative_to(path).as_posix(): sha256(p) for p in sorted(path.rglob("*")) if p.is_file()}
    if not files:
        raise ValueError(f"Empty artifact directory: {path}")
    return {"files": files, "sha256": digest(files)}


def source_snapshot():
    paths = sorted({*ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/**/*.py"),
                    *ROOT.glob("config/*.yaml"), ROOT / "requirements.txt",
                    ROOT / "requirements-experiments.txt", ROOT / "pyproject.toml"})
    paths = [path for path in paths if path.is_file()]
    files = {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths}
    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
        except (OSError, subprocess.CalledProcessError):
            return "unknown"
    return {"git_revision": git("rev-parse", "HEAD"), "dirty_status": git("status", "--porcelain"),
            "files": files, "sha256": digest(files)}
