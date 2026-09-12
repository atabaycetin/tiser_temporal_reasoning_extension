"""Export tennis training examples for offline supervised trace generation."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_INPUT = Path("data/tennis/tennis_train.json")
DEFAULT_OUTPUT_DIR = Path(
    "results/tennis_domain_adaptation/trace_generation/batches_full"
)
DEFAULT_EXCLUDE_FILES = (
    Path("data/tennis/tennis_train_traced_50.json"),
    Path("results/tennis_domain_adaptation/trace_generation/generated_traces_50.jsonl"),
)
DEFAULT_BATCH_SIZE = 50


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def load_json_array(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: record {index} is not an object")
        records.append(item)
    return records


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"{path}: line {line_number} is not an object")
            records.append(item)
    return records


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return load_jsonl(path)
    return load_json_array(path)


def collect_question_ids(records: list[dict[str, Any]], *, path: Path | None = None) -> set[str]:
    ids: set[str] = set()
    source = str(path) if path is not None else "records"
    for index, record in enumerate(records, start=1):
        question_id = record.get("question_id")
        if not isinstance(question_id, str) or not question_id.strip():
            raise ValueError(f"{source}: record {index} is missing non-empty question_id")
        ids.add(question_id.strip())
    return ids


def load_excluded_ids(paths: list[Path]) -> set[str]:
    excluded_ids: set[str] = set()
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Exclude file does not exist: {path}")
        excluded_ids.update(collect_question_ids(load_records(path), path=path))
    return excluded_ids


def extract_context(record: dict[str, Any], *, index: int) -> str:
    context = record.get("context")
    if isinstance(context, str) and context.strip():
        return context.strip()

    prompt = record.get("prompt")
    if isinstance(prompt, str):
        start_marker = "Temporal context:\n"
        end_marker = "\n\nQuestion:"
        if start_marker in prompt and end_marker in prompt:
            context_text = prompt.split(start_marker, 1)[1].split(end_marker, 1)[0].strip()
            if context_text:
                return context_text

    raise ValueError(f"record {index} has no context and no extractable prompt context")


def required_string(record: dict[str, Any], key: str, *, index: int) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"record {index} is missing non-empty {key}")
    return value.strip()


def build_generation_prompt(record: dict[str, Any], *, index: int) -> str:
    context = extract_context(record, index=index)
    question = required_string(record, "question", index=index)
    answer = required_string(record, "answer", index=index)
    category = str(record.get("category", "unknown")).strip() or "unknown"
    return "\n".join(
        [
            "Generate one supervised TISER-style tennis temporal reasoning trace.",
            "Use only the provided temporal context. Do not invent events or add facts from outside it.",
            "The gold answer is provided because this is supervised trace construction.",
            "Do not change the gold answer.",
            "Return only one JSONL line with question_id and output.",
            "",
            "The output value must use this exact TISER-style structure:",
            "<reasoning>",
            "Concise reasoning over the temporal relation.",
            "<timeline>Ordered events needed to answer the question.</timeline>",
            "<reflection>Brief verification that the answer follows from the timeline.</reflection>",
            "</reasoning>",
            f"<answer>{answer}</answer>",
            "",
            "Required JSONL line schema:",
            f'{{"question_id":"{required_string(record, "question_id", index=index)}","output":"<reasoning>...</reasoning>\\n<answer>{answer}</answer>"}}',
            "",
            f"Category: {category}",
            "",
            "Temporal context:",
            context,
            "",
            "Question:",
            question,
            "",
            "Gold answer:",
            answer,
        ]
    )


def parse_limit(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        if value < 1:
            raise ValueError("--limit must be at least 1 or 'all'")
        return value
    text = value.strip().lower()
    if text == "all":
        return None
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValueError("--limit must be a positive integer or 'all'") from exc
    if parsed < 1:
        raise ValueError("--limit must be at least 1 or 'all'")
    return parsed


def select_untraced_records(
    records: list[dict[str, Any]], *, excluded_ids: set[str], limit: str | int | None = None
) -> list[dict[str, Any]]:
    parsed_limit = parse_limit(limit)
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        question_id = required_string(record, "question_id", index=index)
        if question_id in seen_ids:
            raise ValueError(f"duplicate question_id in input: {question_id}")
        seen_ids.add(question_id)
        if question_id in excluded_ids:
            continue
        selected.append(record)
        if parsed_limit is not None and len(selected) >= parsed_limit:
            break
    return selected


def build_rows(records: list[dict[str, Any]], *, start_index: int = 1) -> list[dict[str, Any]]:
    rows = []
    for index, record in enumerate(records, start=start_index):
        rows.append(
            {
                "question_id": required_string(record, "question_id", index=index),
                "dataset_name": required_string(record, "dataset_name", index=index),
                "category": str(record.get("category", "unknown")).strip() or "unknown",
                "context": extract_context(record, index=index),
                "question": required_string(record, "question", index=index),
                "gold_answer": required_string(record, "answer", index=index),
                "prompt": build_generation_prompt(record, index=index),
            }
        )
    return rows


def build_request_rows(
    records: list[dict[str, Any]], *, limit: int, offset: int
) -> list[dict[str, Any]]:
    if offset < 0:
        raise ValueError("--offset must be non-negative")
    parsed_limit = parse_limit(limit)
    if parsed_limit is None:
        selected = records[offset:]
    else:
        selected = records[offset : offset + parsed_limit]
    return build_rows(selected, start_index=offset + 1)


def split_batches(rows: list[dict[str, Any]], *, batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    return [rows[index : index + batch_size] for index in range(0, len(rows), batch_size)]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Tennis Trace Generation Batch",
        "",
        "Generate one strict trace per example. Do not call APIs automatically from this file.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['question_id']}",
                "",
                f"- Dataset: `{row['dataset_name']}`",
                f"- Category: `{row['category']}`",
                f"- Gold answer: `{row['gold_answer']}`",
                "",
                "```text",
                row["prompt"],
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def batch_filename(batch_number: int, output_format: str) -> str:
    extension = "jsonl" if output_format == "jsonl" else "md"
    return f"batch_{batch_number:03d}.{extension}"


def write_batches(
    output_dir: Path, rows: list[dict[str, Any]], *, batch_size: int, output_format: str
) -> list[dict[str, Any]]:
    batches = split_batches(rows, batch_size=batch_size)
    batch_manifest: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for batch_number, batch_rows in enumerate(batches, start=1):
        filename = batch_filename(batch_number, output_format)
        output_path = output_dir / filename
        if output_format == "markdown":
            write_markdown(output_path, batch_rows)
        else:
            write_jsonl(output_path, batch_rows)
        batch_manifest.append(
            {
                "file": filename,
                "question_ids": [row["question_id"] for row in batch_rows],
            }
        )
    return batch_manifest


def build_manifest(
    *,
    records: list[dict[str, Any]],
    excluded_ids: set[str],
    rows: list[dict[str, Any]],
    batch_size: int,
    batches: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_question_ids = [row["question_id"] for row in rows]
    counts_by_category = Counter(str(row["category"]) for row in rows)
    return {
        "total_train_examples": len(records),
        "excluded_ids_count": len(excluded_ids),
        "selected_count": len(rows),
        "batch_size": batch_size,
        "number_of_batches": len(batches),
        "selected_question_ids": selected_question_ids,
        "counts_by_category": dict(sorted(counts_by_category.items())),
        "batches": batches,
    }


def write_manifest(output_dir: Path, manifest: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def prepare_batches(
    *,
    input_path: Path,
    output_dir: Path,
    exclude_files: list[Path],
    batch_size: int,
    limit: str | int | None,
    output_format: str,
) -> dict[str, Any]:
    records = load_json_array(input_path)
    excluded_ids = load_excluded_ids(exclude_files)
    selected_records = select_untraced_records(records, excluded_ids=excluded_ids, limit=limit)
    rows = build_rows(selected_records)
    selected_ids = [row["question_id"] for row in rows]
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected rows contain duplicate question_ids")
    batches = write_batches(output_dir, rows, batch_size=batch_size, output_format=output_format)
    manifest = build_manifest(
        records=records,
        excluded_ids=excluded_ids,
        rows=rows,
        batch_size=batch_size,
        batches=batches,
    )
    write_manifest(output_dir, manifest)
    return manifest


def parse_exclude_files(values: list[str] | None) -> list[Path]:
    if not values:
        return [resolve_repo_path(path) for path in DEFAULT_EXCLUDE_FILES]
    paths: list[Path] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item:
                paths.append(resolve_repo_path(item))
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare offline prompts for tennis trace generation."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Base tennis train JSON array.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for numbered batch files and manifest.json.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of examples per batch.",
    )
    parser.add_argument(
        "--exclude-files",
        nargs="*",
        default=None,
        help="JSON/JSONL files whose question_ids should be excluded. Comma-separated values are also accepted.",
    )
    parser.add_argument(
        "--limit",
        default="all",
        help="Number of untraced examples to export, or 'all'. Defaults to all remaining examples.",
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "markdown"),
        default="jsonl",
        help="Batch output format.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = resolve_repo_path(args.input)
    output_dir = resolve_repo_path(args.output_dir)
    exclude_files = parse_exclude_files(args.exclude_files)
    manifest = prepare_batches(
        input_path=input_path,
        output_dir=output_dir,
        exclude_files=exclude_files,
        batch_size=args.batch_size,
        limit=args.limit,
        output_format=args.format,
    )

    print(f"Input: {relative_or_absolute(input_path)}")
    print(f"Excluded question_ids: {manifest['excluded_ids_count']}")
    print(f"Exported examples: {manifest['selected_count']}")
    print(f"Batches: {manifest['number_of_batches']}")
    print(f"Output directory: {relative_or_absolute(output_dir)}")
    print("No external API was called.")


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
