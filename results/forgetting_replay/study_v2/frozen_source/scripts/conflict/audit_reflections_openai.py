"""Run a blinded, resumable, fully automated reflection audit with OpenAI.

The judge sees only the extracted reflection text and a pseudonymous audit ID.
Conflict type, model condition, answers, and correctness are joined back only
after judging. Two independent rubric passes are run for every scorable unique
reflection; disagreements are sent to a third adjudication pass.

The script uses the Responses REST API through the Python standard library so
the repository does not need an SDK dependency. It never stores the API key.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.audit.reflection import (
    ADJUDICATOR_PROMPT,
    JUDGMENT_SCHEMA,
    LABELS,
    MENTION_KINDS,
    PASS_PROMPTS,
    PROMPT_VERSION,
    summarize_rows,
    validate_judgment,
)


DEFAULT_SCORED_FILES = (
    Path("results/context_memory_conflict/scored/base__tiser.jsonl"),
    Path("results/context_memory_conflict/scored/tiser__tiser.jsonl"),
)
DEFAULT_OUTPUT_DIR = Path("results/context_memory_conflict/scored/audit")
DEFAULT_MODEL = "gpt-5.6-sol"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scored_paths = [resolve_path(path) for path in args.scored_files]
    output_dir = resolve_path(args.output_dir)
    rows_by_cell = load_cells(scored_paths, limit=args.limit)
    all_rows = [row for rows in rows_by_cell.values() for row in rows]
    reflections = collect_reflections(all_rows)

    targets = output_paths(output_dir, rows_by_cell)
    guard_outputs(targets, resume=args.resume, force=args.force, prepare_only=args.prepare_only)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.force:
        for target in targets:
            if target.exists():
                target.unlink()

    jobs = build_primary_jobs(reflections, args.model)
    run_spec = build_run_spec(args, scored_paths, jobs)
    write_or_validate_run_spec(output_dir / "run_spec.json", run_spec, resume=args.resume)
    write_text(output_dir / "judge_prompt.txt", render_prompt_record(args.model))
    write_jsonl(output_dir / "requests.jsonl", [job["request_record"] for job in jobs])
    if args.prepare_only:
        write_prepare_summary(output_dir, rows_by_cell, reflections, jobs, args)
        print(f"[reflection-audit] prepared {len(jobs)} blinded requests; no API calls made")
        return 0

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"Environment variable {args.api_key_env} is not set. "
            "Use --prepare-only to inspect requests without an API key."
        )

    raw_path = output_dir / "raw_responses.jsonl"
    cached = load_response_cache(raw_path) if args.resume else {}
    primary = execute_jobs(jobs, cached, raw_path, api_key, args)
    adjudication_jobs = build_adjudication_jobs(reflections, primary, args.model)
    append_jsonl(
        output_dir / "requests.jsonl",
        [job["request_record"] for job in adjudication_jobs],
    )
    adjudicated = execute_jobs(adjudication_jobs, cached, raw_path, api_key, args)

    final_by_hash = finalize_judgments(reflections, primary, adjudicated)
    audit_rows_by_cell = {
        cell: [build_audit_row(row, final_by_hash, primary) for row in rows]
        for cell, rows in rows_by_cell.items()
    }
    for cell, rows in audit_rows_by_cell.items():
        write_csv(output_dir / f"{cell}.audit.csv", rows)

    summary = build_summary(audit_rows_by_cell, primary, adjudicated, args, scored_paths)
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "run_meta.json", build_run_meta(args, scored_paths, summary))
    print_summary(summary)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scored-files",
        nargs="+",
        default=[path.as_posix() for path in DEFAULT_SCORED_FILES],
        help="One or more scored TISER-prompt JSONL files.",
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR.as_posix())
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None, help="Debug limit per cell.")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Write blinded request artifacts without making API calls.",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.max_retries < 1:
        parser.error("--max-retries must be at least 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.resume and args.force:
        parser.error("--resume and --force are mutually exclusive")
    return args


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    return rows


def load_cells(paths: list[Path], *, limit: int | None) -> dict[str, list[dict[str, Any]]]:
    result = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        rows = read_jsonl(path)
        if limit is not None:
            rows = rows[:limit]
        for index, row in enumerate(rows):
            row["_source_index"] = index
            row["_cell"] = path.stem
        result[path.stem] = rows
    return result


def reflection_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_reflections(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        text = str(row.get("reflection_text") or "")
        digest = reflection_hash(text)
        malformed = bool(row.get("reflection_malformed")) or not text.strip()
        result.setdefault(digest, {"text": text, "malformed": malformed})
        result[digest]["malformed"] = result[digest]["malformed"] and malformed
    return result


def blinded_id(digest: str) -> str:
    return f"reflection-{digest[:16]}"


def build_primary_jobs(
    reflections: dict[str, dict[str, Any]], model: str
) -> list[dict[str, Any]]:
    jobs = []
    for digest, source in sorted(reflections.items()):
        if source["malformed"]:
            continue
        for pass_name, instructions in PASS_PROMPTS.items():
            input_text = render_blinded_input(digest, source["text"])
            jobs.append(make_job(digest, pass_name, model, instructions, input_text))
    return jobs


def build_adjudication_jobs(
    reflections: dict[str, dict[str, Any]],
    primary: dict[str, dict[str, Any]],
    model: str,
) -> list[dict[str, Any]]:
    jobs = []
    for digest, source in sorted(reflections.items()):
        if source["malformed"]:
            continue
        a = primary[job_key(digest, "judge_a")]["parsed"]
        b = primary[job_key(digest, "judge_b")]["parsed"]
        if a["label"] == b["label"]:
            continue
        input_text = (
            render_blinded_input(digest, source["text"])
            + "\n\nJUDGE A:\n"
            + json.dumps(a, ensure_ascii=False)
            + "\nJUDGE B:\n"
            + json.dumps(b, ensure_ascii=False)
        )
        jobs.append(make_job(digest, "adjudicator", model, ADJUDICATOR_PROMPT, input_text))
    return jobs


def render_blinded_input(digest: str, reflection: str) -> str:
    return (
        f"AUDIT_ID: {blinded_id(digest)}\n"
        "REFLECTION_START\n"
        f"{reflection}\n"
        "REFLECTION_END"
    )


def make_job(
    digest: str,
    pass_name: str,
    model: str,
    instructions: str,
    input_text: str,
) -> dict[str, Any]:
    key = job_key(digest, pass_name)
    payload = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "reflection_conflict_judgment",
                "schema": JUDGMENT_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": 500,
        "store": False,
        "metadata": {
            "audit_id": blinded_id(digest),
            "judge_pass": pass_name,
            "prompt_version": PROMPT_VERSION,
        },
    }
    request_sha256 = canonical_json_sha256(payload)
    return {
        "job_key": key,
        "request_sha256": request_sha256,
        "reflection_sha256": digest,
        "pass": pass_name,
        "payload": payload,
        "request_record": {
            "job_key": key,
            "request_sha256": request_sha256,
            "reflection_sha256": digest,
            "pass": pass_name,
            "payload": payload,
        },
    }


def job_key(digest: str, pass_name: str) -> str:
    return f"{digest}:{pass_name}"


def execute_jobs(
    jobs: list[dict[str, Any]],
    cached: dict[str, dict[str, Any]],
    raw_path: Path,
    api_key: str,
    args: argparse.Namespace,
) -> dict[str, dict[str, Any]]:
    for job in jobs:
        record = cached.get(job["job_key"])
        if record is not None and record.get("request_sha256") != job["request_sha256"]:
            raise RuntimeError(
                "Cached response does not match the current model, prompt, schema, "
                f"and input for {job['job_key']}; use a new output directory."
            )
    results = {key: value for key, value in cached.items()}
    pending = [job for job in jobs if job["job_key"] not in results]
    write_lock = threading.Lock()

    def execute(job: dict[str, Any]) -> dict[str, Any]:
        validation_failures = []
        for attempt in range(args.max_retries):
            response = call_with_retries(job["payload"], api_key, args)
            try:
                parsed = parse_response(response)
                validate_judgment(parsed, extract_reflection(job["payload"]["input"]))
            except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                validation_failures.append(
                    {"attempt": attempt + 1, "error": str(exc), "response": response}
                )
                if attempt + 1 == args.max_retries:
                    raise RuntimeError(
                        f"Judge output remained invalid after {args.max_retries} "
                        f"attempts for {job['job_key']}: {exc}"
                    ) from exc
                time.sleep(min(5.0, 2.0**attempt) + random.random())
                continue
            return {
                "job_key": job["job_key"],
                "request_sha256": job["request_sha256"],
                "reflection_sha256": job["reflection_sha256"],
                "pass": job["pass"],
                "parsed": parsed,
                "response": response,
                "validation_failures": validation_failures,
            }
        raise AssertionError("unreachable")

    if pending:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(execute, job): job for job in pending}
            for completed, future in enumerate(as_completed(futures), start=1):
                record = future.result()
                results[record["job_key"]] = record
                with write_lock:
                    append_jsonl(raw_path, [record])
                if completed % 25 == 0 or completed == len(pending):
                    print(f"[reflection-audit] completed {completed}/{len(pending)} pending calls")

    return {job["job_key"]: results[job["job_key"]] for job in jobs}


def call_with_retries(
    payload: dict[str, Any], api_key: str, args: argparse.Namespace
) -> dict[str, Any]:
    error: Exception | None = None
    for attempt in range(args.max_retries):
        try:
            request = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=args.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            error = RuntimeError(f"OpenAI HTTP {exc.code}: {detail}")
            if exc.code < 500 and exc.code != 429:
                raise error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            error = exc
        if attempt + 1 < args.max_retries:
            delay = min(30.0, 2.0**attempt) + random.random()
            time.sleep(delay)
    raise RuntimeError(f"OpenAI request failed after {args.max_retries} attempts: {error}")


def parse_response(response: dict[str, Any]) -> dict[str, Any]:
    text = response.get("output_text")
    if not isinstance(text, str):
        parts = []
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    parts.append(content["text"])
                if content.get("type") == "refusal":
                    raise RuntimeError(f"Judge refusal: {content.get('refusal', '')}")
        text = "".join(parts)
    if not text:
        raise ValueError("OpenAI response contains no output text")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Structured output is not an object")
    return value


def extract_reflection(input_text: str) -> str:
    start = input_text.index("REFLECTION_START\n") + len("REFLECTION_START\n")
    end = input_text.index("\nREFLECTION_END", start)
    return input_text[start:end]


def finalize_judgments(
    reflections: dict[str, dict[str, Any]],
    primary: dict[str, dict[str, Any]],
    adjudicated: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result = {}
    for digest, source in reflections.items():
        if source["malformed"]:
            result[digest] = {
                "label": "unscorable",
                "mention_kind": "none",
                "evidence_quote": "",
                "rationale": "Source reflection was empty or structurally malformed.",
                "decision_source": "source_validation",
            }
            continue
        a = primary[job_key(digest, "judge_a")]["parsed"]
        b = primary[job_key(digest, "judge_b")]["parsed"]
        if a["label"] == b["label"]:
            selected = dict(a)
            selected["decision_source"] = "two_pass_agreement"
        else:
            selected = dict(adjudicated[job_key(digest, "adjudicator")]["parsed"])
            selected["decision_source"] = "adjudicator"
        result[digest] = selected
    return result


def build_audit_row(
    row: dict[str, Any],
    final_by_hash: dict[str, dict[str, Any]],
    primary: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    reflection = str(row.get("reflection_text") or "")
    digest = reflection_hash(reflection)
    final = final_by_hash[digest]
    malformed = final["label"] == "unscorable"
    positive = final["label"] == "explicit_conflict"
    a = primary.get(job_key(digest, "judge_a"), {}).get("parsed", {})
    b = primary.get(job_key(digest, "judge_b"), {}).get("parsed", {})
    return {
        "id": row.get("id", ""),
        "conflict_type": row.get("conflict_type", ""),
        "model": row.get("model", ""),
        "style": row.get("style", ""),
        "faithful_em": row.get("faithful_em", ""),
        "memorised_em": row.get("memorised_em", ""),
        "reflection_malformed": row.get("reflection_malformed", False),
        "reflection_mentions_conflict": row.get("reflection_mentions_conflict", False),
        "reflection_text": reflection,
        "reflection_sha256": digest,
        "judge_a_label": a.get("label", ""),
        "judge_b_label": b.get("label", ""),
        "adjudicated": final["decision_source"] == "adjudicator",
        "final_label": final["label"],
        "agent_reflection_conflict_audit": "" if malformed else int(positive),
        "conflict_kind": final["mention_kind"],
        "evidence_quote": final["evidence_quote"],
        "agent_rationale": final["rationale"],
    }


def build_summary(
    rows_by_cell: dict[str, list[dict[str, Any]]],
    primary: dict[str, dict[str, Any]],
    adjudicated: dict[str, dict[str, Any]],
    args: argparse.Namespace,
    scored_paths: list[Path],
) -> dict[str, Any]:
    cells = {cell: summarize_rows(rows) for cell, rows in rows_by_cell.items()}
    usage = Counter()
    actual_models = Counter()
    for result in [*primary.values(), *adjudicated.values()]:
        responses = [failure["response"] for failure in result.get("validation_failures", [])]
        responses.append(result["response"])
        for response in responses:
            actual_models[str(response.get("model", "unknown"))] += 1
            for key, value in (response.get("usage") or {}).items():
                if isinstance(value, int):
                    usage[key] += value
    return {
        "prompt_version": PROMPT_VERSION,
        "requested_model": args.model,
        "actual_response_models": dict(actual_models),
        "scored_files": [relative_path(path) for path in scored_paths],
        "input_sha256": {relative_path(path): sha256_file(path) for path in scored_paths},
        "prompt_sha256": hashlib.sha256(render_prompt_record(args.model).encode()).hexdigest(),
        "primary_calls": len(primary),
        "adjudication_calls": len(adjudicated),
        "provider_calls_including_invalid_retries": sum(actual_models.values()),
        "usage": dict(usage),
        "cells": cells,
        "interpretation": (
            "This is a new automated judge estimate, not a reproduction of the "
            "historical Claude result. Two passes and adjudication reduce random "
            "label instability but do not remove shared model-judge bias."
        ),
    }


def output_paths(output_dir: Path, rows_by_cell: dict[str, list[dict[str, Any]]]) -> list[Path]:
    return [
        output_dir / "judge_prompt.txt",
        output_dir / "requests.jsonl",
        output_dir / "run_spec.json",
        output_dir / "prepare_summary.json",
        output_dir / "raw_responses.jsonl",
        output_dir / "summary.json",
        output_dir / "run_meta.json",
        *[output_dir / f"{cell}.audit.csv" for cell in rows_by_cell],
    ]


def guard_outputs(
    paths: list[Path], *, resume: bool, force: bool, prepare_only: bool
) -> None:
    ignored = {"raw_responses.jsonl", "summary.json", "run_meta.json"} if prepare_only else set()
    existing = [path for path in paths if path.exists() and path.name not in ignored]
    if existing and not resume and not force:
        joined = ", ".join(relative_path(path) for path in existing)
        raise FileExistsError(f"Audit outputs already exist: {joined}; use --resume or --force")


def load_response_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {row["job_key"]: row for row in read_jsonl(path)}


def write_prepare_summary(
    output_dir: Path,
    rows_by_cell: dict[str, list[dict[str, Any]]],
    reflections: dict[str, dict[str, Any]],
    jobs: list[dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    write_json(
        output_dir / "prepare_summary.json",
        {
            "model": args.model,
            "prompt_version": PROMPT_VERSION,
            "cells": {cell: len(rows) for cell, rows in rows_by_cell.items()},
            "unique_reflections": len(reflections),
            "malformed_or_empty_unique_reflections": sum(
                source["malformed"] for source in reflections.values()
            ),
            "primary_requests": len(jobs),
            "note": "No provider calls were made.",
        },
    )


def build_run_meta(
    args: argparse.Namespace,
    scored_paths: list[Path],
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv],
        "model": args.model,
        "prompt_version": PROMPT_VERSION,
        "workers": args.workers,
        "timeout_seconds": args.timeout_seconds,
        "max_retries": args.max_retries,
        "scored_files": [relative_path(path) for path in scored_paths],
        "git": git_snapshot(),
        "summary_sha256": hashlib.sha256(
            json.dumps(summary, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "api_key_stored": False,
    }


def build_run_spec(
    args: argparse.Namespace,
    scored_paths: list[Path],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the immutable portion of a run, used to guard safe resumption."""

    return {
        "model": args.model,
        "prompt_version": PROMPT_VERSION,
        "limit_per_cell": args.limit,
        "scored_files": [relative_path(path) for path in scored_paths],
        "input_sha256": {relative_path(path): sha256_file(path) for path in scored_paths},
        "primary_request_sha256": {
            job["job_key"]: job["request_sha256"] for job in jobs
        },
    }


def write_or_validate_run_spec(path: Path, value: dict[str, Any], *, resume: bool) -> None:
    if resume:
        if not path.is_file():
            raise RuntimeError(
                f"Cannot safely resume because {relative_path(path)} is missing; "
                "use a new output directory."
            )
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous != value:
            raise RuntimeError(
                "Cannot resume: model, prompt, input files, limit, or request "
                "payloads differ from the frozen run specification."
            )
        return
    write_json(path, value)


def git_snapshot() -> dict[str, Any]:
    def run(*command: str) -> str:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    return {
        "commit": run("git", "rev-parse", "HEAD"),
        "dirty": bool(run("git", "status", "--porcelain")),
    }


def render_prompt_record(model: str) -> str:
    sections = [
        f"prompt_version: {PROMPT_VERSION}",
        f"requested_model: {model}",
        "",
    ]
    for name, prompt in PASS_PROMPTS.items():
        sections.extend([f"[{name}]", prompt, ""])
    sections.extend(["[adjudicator]", ADJUDICATOR_PROMPT, "", "[json_schema]", json.dumps(JUDGMENT_SCHEMA, indent=2, sort_keys=True)])
    return "\n".join(sections) + "\n"


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(summary: dict[str, Any]) -> None:
    print("[reflection-audit] completed")
    for cell, values in summary["cells"].items():
        genuine = values["genuine_conflicts"]
        print(
            f"  {cell}: explicit conflict {genuine['count']}/{genuine['n']} "
            f"= {genuine['rate']:.3%}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
