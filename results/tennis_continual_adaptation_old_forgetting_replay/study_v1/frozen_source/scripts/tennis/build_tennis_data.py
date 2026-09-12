"""Build tennis-domain temporal QA prompt records."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tennis.build_dataset import convert_examples, load_audited_examples, write_json
from tennis.prompts import build_reported_tennis_prompt, build_tennis_prompt


def main() -> None:
    parser = argparse.ArgumentParser(description="Build tennis temporal QA datasets.")
    parser.add_argument(
        "--input",
        default="data/tennis/processed/tennis_raw_audited.json",
        help="Path to audited tennis raw JSON array.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/tennis/processed",
        help="Directory for converted tennis dataset files.",
    )
    parser.add_argument(
        "--dataset-name",
        default="tennis_temporal",
        help="Value to store in dataset_name.",
    )
    parser.add_argument(
        "--deterministic-output",
        action="store_true",
        help="Add conservative placeholder TISER outputs with gold answers.",
    )
    parser.add_argument(
        "--summary-dir",
        default="results/tennis_domain_adaptation/processed",
        help="Directory for conversion summary JSON.",
    )
    parser.add_argument(
        "--prompt-version",
        choices=("strict", "reported"),
        default="strict",
        help=(
            "Use the current strict-XML instruction or the historical wording stored "
            "in the data used for the reported training runs."
        ),
    )
    args = parser.parse_args()

    examples = load_audited_examples(args.input)
    prompt_builder = (
        build_reported_tennis_prompt
        if args.prompt_version == "reported"
        else build_tennis_prompt
    )
    tiser_records, standard_records, summary = convert_examples(
        examples,
        dataset_name=args.dataset_name,
        deterministic_output=args.deterministic_output,
        tiser_prompt_builder=prompt_builder,
    )

    output_dir = Path(args.output_dir)
    summary_dir = Path(args.summary_dir)
    tiser_path = output_dir / "tennis_all_tiser.json"
    standard_path = output_dir / "tennis_all_standard_prompt.json"
    summary_path = summary_dir / "tennis_conversion_summary.json"

    summary.update(
        {
            "input_path": str(Path(args.input)),
            "tiser_output_path": str(tiser_path),
            "standard_prompt_output_path": str(standard_path),
            "summary_path": str(summary_path),
            "dataset_name": args.dataset_name,
            "prompt_version": args.prompt_version,
        }
    )

    write_json(tiser_path, tiser_records)
    write_json(standard_path, standard_records)
    write_json(summary_path, summary)

    print(f"Loaded audited examples: {summary['input_count']}")
    print(f"Converted examples: {summary['converted_count']}")
    print(f"Validation errors: {summary['validation_error_count']}")
    print(f"Defaulted source fields: {summary['source_defaulted_count']}")
    print(f"Wrote TISER records: {tiser_path}")
    print(f"Wrote standard prompt records: {standard_path}")
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
