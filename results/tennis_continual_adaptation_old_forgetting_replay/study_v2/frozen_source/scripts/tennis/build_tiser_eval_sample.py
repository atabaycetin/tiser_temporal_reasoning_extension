"""Build a fixed original-TISER evaluation sample for forgetting analysis."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = Path(
    "results/tennis_domain_adaptation/processed/tiser_eval_sample_summary.json"
)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = resolve_repo_path(args.input)
    output_path = resolve_repo_path(args.output)
    complement_path = (
        resolve_repo_path(args.complement_output) if args.complement_output else None
    )
    summary_path = resolve_repo_path(args.summary)

    if output_path.exists() and not args.force:
        raise FileExistsError(f"{args.output} exists; pass --force to overwrite it.")
    if complement_path is not None and complement_path.exists() and not args.force:
        raise FileExistsError(
            f"{args.complement_output} exists; pass --force to overwrite it."
        )
    if summary_path.exists() and not args.force:
        raise FileExistsError(f"{args.summary} exists; pass --force to overwrite it.")

    rows = load_records(input_path)
    sampled, summary = sample_records(rows, per_split=args.per_split, seed=args.seed)
    complement = build_complement(rows, sampled)
    summary.update(
        {
            "input": relative_path(input_path),
            "output": relative_path(output_path),
            "complement_output": (
                relative_path(complement_path) if complement_path is not None else None
            ),
            "n_complement": len(complement),
            "summary": relative_path(summary_path),
            "seed": args.seed,
            "per_split": args.per_split,
        }
    )

    write_json(output_path, sampled)
    if complement_path is not None:
        write_json(complement_path, complement)
    write_json(summary_path, summary)

    if summary["warnings"]:
        for warning in summary["warnings"]:
            print(f"[tiser-sample] WARNING: {warning}")
    print(f"[tiser-sample] wrote {len(sampled)} examples to {args.output}")
    if complement_path is not None:
        print(
            f"[tiser-sample] wrote {len(complement)} complement examples to "
            f"{args.complement_output}"
        )
    print(f"[tiser-sample] wrote summary to {args.summary}")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sample original TISER test records for forgetting evaluation."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--complement-output",
        default=None,
        help=(
            "Optional path for every input record not selected. Writing this at "
            "selection time freezes a disjoint final-evaluation population."
        ),
    )
    parser.add_argument("--per-split", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--summary", default=SUMMARY_PATH.as_posix())
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON array in {path}")
        return require_dicts(data, path)

    rows = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Line {line_number} in {path} is not a JSON object")
        rows.append(row)
    return rows


def require_dicts(data: list[Any], path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Record {index} in {path} is not a JSON object")
        rows.append(row)
    return rows


def sample_records(
    rows: list[dict[str, Any]], *, per_split: int, seed: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    warnings: list[str] = []
    rows_with_split = [row for row in rows if split_name(row)]

    if rows and len(rows_with_split) == len(rows):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[split_name(row)].append(row)

        selected: list[dict[str, Any]] = []
        split_summary = {}
        for split in sorted(grouped):
            split_rows = list(grouped[split])
            rng.shuffle(split_rows)
            take = min(per_split, len(split_rows))
            selected_rows = split_rows[:take]
            selected.extend(selected_rows)
            split_summary[split] = {"available": len(split_rows), "sampled": take}
    else:
        warnings.append(
            "No complete dataset_name/split field was available; sampled globally instead."
        )
        shuffled = list(rows)
        rng.shuffle(shuffled)
        selected = shuffled[: min(per_split, len(shuffled))]
        split_summary = {"GLOBAL": {"available": len(rows), "sampled": len(selected)}}

    projected = [project_record(row, index) for index, row in enumerate(selected, start=1)]
    return projected, {
        "n_input": len(rows),
        "n_output": len(projected),
        "sampling_mode": "per_split" if rows and len(rows_with_split) == len(rows) else "global",
        "split_summary": split_summary,
        "dataset_name_counts": dict(Counter(row.get("dataset_name", "MISSING") for row in projected)),
        "warnings": warnings,
        "fields": ["prompt", "question", "answer", "dataset_name", "question_id"],
    }


def split_name(row: dict[str, Any]) -> str:
    value = row.get("dataset_name", row.get("split"))
    return str(value).strip() if value is not None else ""


def project_record(row: dict[str, Any], index: int) -> dict[str, Any]:
    answer = row.get("answer", row.get("gold", ""))
    return {
        "prompt": row.get("prompt", ""),
        "question": row.get("question", ""),
        "answer": "" if answer is None else str(answer),
        "dataset_name": row.get("dataset_name", row.get("split", "original_tiser")),
        "question_id": row.get("question_id", f"original_tiser_sample_{index:05d}"),
    }


def build_complement(
    rows: list[dict[str, Any]], sampled: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return the original-order complement using stable split/question IDs."""

    identities: list[tuple[str, str]] = []
    for index, row in enumerate(rows, start=1):
        dataset_name = split_name(row)
        question_id = str(row.get("question_id") or "").strip()
        if not dataset_name or not question_id:
            raise ValueError(
                "A complement requires non-empty dataset_name/split and question_id "
                f"for every input record; record {index} is incomplete."
            )
        identities.append((dataset_name, question_id))
    if len(set(identities)) != len(identities):
        raise ValueError(
            "A complement requires unique (dataset_name, question_id) pairs."
        )

    sampled_identities = {
        (str(row["dataset_name"]), str(row["question_id"])) for row in sampled
    }
    if len(sampled_identities) != len(sampled):
        raise ValueError("The sampled selection contains duplicate stable IDs.")
    unknown = sampled_identities - set(identities)
    if unknown:
        raise ValueError(f"Sampled IDs are absent from the input: {sorted(unknown)[:3]}")

    return [
        project_record(row, index)
        for index, (row, identity) in enumerate(zip(rows, identities), start=1)
        if identity not in sampled_identities
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
