"""Aggregate tennis adaptation results and forgetting metrics."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = Path("results/tennis_domain_adaptation")
COMPARISONS_DIR = RESULTS_ROOT / "comparisons"
CONDITIONS = ["base_qwen", "original_tiser", "tennis_only", "mixed_replay"]
EVENT_ORDERING_CATEGORIES = {
    "yes_no_before_after",
    "which_first_last",
    "immediate_before_after",
    "tournament_round_sequence",
}
MISSING = "MISSING"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results_root = resolve_repo_path(args.results_dir)
    output_dir = resolve_repo_path(args.output_dir)
    outputs = output_paths(output_dir)
    guard_outputs(outputs, force=args.force)

    tennis_metrics = {
        condition: load_metrics(results_root / "scored" / condition / "metrics.json")
        for condition in CONDITIONS
    }
    original_metrics = {
        condition: load_original_sample_metrics(results_root, condition)
        for condition in CONDITIONS
    }

    summary = build_summary(tennis_metrics, original_metrics)
    category_rows = build_category_rows(tennis_metrics)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_text(outputs["table_md"], render_final_table(summary["rows"]))
    write_csv(outputs["table_csv"], summary["rows"], FINAL_TABLE_FIELDS)
    write_json(outputs["summary_json"], summary)
    write_text(outputs["forgetting_md"], render_forgetting(summary["rows"], original_metrics))
    write_text(outputs["category_md"], render_category_analysis(category_rows, tennis_metrics))

    print("[tennis-aggregate] wrote:")
    for path in outputs.values():
        print(f"- {relative_path(path)}")
    return 0


FINAL_TABLE_FIELDS = [
    "condition",
    "prompt_style",
    "tennis_em",
    "tennis_f1",
    "tennis_malformed_rate",
    "original_tiser_em",
    "original_tiser_f1",
    "forgetting_delta_em",
    "notes",
]


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate final tennis domain-adaptation result tables."
    )
    parser.add_argument("--results-dir", default=RESULTS_ROOT.as_posix())
    parser.add_argument("--output-dir", default=COMPARISONS_DIR.as_posix())
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "table_md": output_dir / "final_results_table.md",
        "table_csv": output_dir / "final_results_table.csv",
        "summary_json": output_dir / "final_results_summary.json",
        "forgetting_md": output_dir / "forgetting_analysis.md",
        "category_md": output_dir / "category_analysis.md",
    }


def guard_outputs(outputs: dict[str, Path], *, force: bool) -> None:
    existing = [path for path in outputs.values() if path.exists()]
    if existing and not force:
        joined = ", ".join(relative_path(path) for path in existing)
        raise FileExistsError(f"Aggregation outputs exist ({joined}); pass --force.")


def load_metrics(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    metrics = json.loads(path.read_text(encoding="utf-8"))
    metrics["_metrics_path"] = relative_path(path)
    return metrics


def load_original_sample_metrics(results_root: Path, condition: str) -> dict[str, Any] | None:
    candidates = [
        results_root / "scored_original_tiser_sample" / condition / "metrics.json",
        results_root / "scored" / "original_tiser_sample" / condition / "metrics.json",
        results_root / "scored" / condition / "original_tiser_sample" / "metrics.json",
        results_root / "scored" / f"{condition}_original_tiser_sample" / "metrics.json",
    ]
    for path in candidates:
        metrics = load_metrics(path)
        if metrics is not None:
            return metrics
    return None


def build_summary(
    tennis_metrics: dict[str, dict[str, Any] | None],
    original_metrics: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    baseline_original = extract_overall(original_metrics["original_tiser"])
    rows = []
    missing_inputs = []

    for condition in CONDITIONS:
        tennis = extract_overall(tennis_metrics[condition])
        original = extract_overall(original_metrics[condition])
        if tennis_metrics[condition] is None:
            missing_inputs.append(f"tennis_test metrics for {condition}")
        if condition != "base_qwen" and original_metrics[condition] is None:
            missing_inputs.append(f"original TISER sample metrics for {condition}")

        notes = []
        if tennis_metrics[condition] is None:
            notes.append("missing tennis_test metrics")
        if condition == "base_qwen":
            notes.append("not scheduled for original TISER forgetting eval")
        elif original_metrics[condition] is None:
            notes.append("missing original TISER sample metrics")

        rows.append(
            {
                "condition": condition,
                "prompt_style": metric_value(tennis_metrics[condition], "prompt_style"),
                "tennis_em": tennis["em"],
                "tennis_f1": tennis["f1"],
                "tennis_malformed_rate": tennis["malformed_rate"],
                "original_tiser_em": original["em"],
                "original_tiser_f1": original["f1"],
                "forgetting_delta_em": delta_or_missing(original["em"], baseline_original["em"]),
                "notes": "; ".join(notes) if notes else "",
            }
        )

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "conditions": CONDITIONS,
        "event_ordering_categories": sorted(EVENT_ORDERING_CATEGORIES),
        "rows": rows,
        "missing_inputs": missing_inputs,
        "metric_paths": {
            condition: {
                "tennis_test": metric_path(tennis_metrics[condition]),
                "original_tiser_sample": metric_path(original_metrics[condition]),
            }
            for condition in CONDITIONS
        },
    }


def extract_overall(metrics: dict[str, Any] | None) -> dict[str, Any]:
    if metrics is None:
        return {"n": MISSING, "em": MISSING, "f1": MISSING, "malformed_rate": MISSING}

    if isinstance(metrics.get("overall"), dict):
        overall = metrics["overall"]
        return {
            "n": overall.get("n", MISSING),
            "em": number_or_missing(overall.get("em")),
            "f1": number_or_missing(overall.get("f1")),
            "malformed_rate": number_or_missing(overall.get("malformed_rate")),
        }

    n_total = metrics.get("n_total", MISSING)
    malformed_rate = MISSING
    if is_number(metrics.get("n_malformed")) and is_number(metrics.get("n_total")):
        malformed_rate = float(metrics["n_malformed"]) / float(metrics["n_total"])
    return {
        "n": n_total,
        "em": number_or_missing(metrics.get("macro_em")),
        "f1": number_or_missing(metrics.get("macro_f1")),
        "malformed_rate": malformed_rate,
    }


def build_category_rows(
    tennis_metrics: dict[str, dict[str, Any] | None]
) -> list[dict[str, Any]]:
    categories = set()
    for metrics in tennis_metrics.values():
        if metrics and isinstance(metrics.get("per_category"), dict):
            categories.update(metrics["per_category"])
    categories = categories or {"MISSING"}

    baseline = tennis_metrics.get("original_tiser") or {}
    baseline_categories = baseline.get("per_category", {}) if isinstance(baseline, dict) else {}
    rows = []
    for condition in CONDITIONS:
        per_category = (
            tennis_metrics[condition].get("per_category", {})
            if tennis_metrics[condition]
            else {}
        )
        for category in sorted(categories):
            values = per_category.get(category)
            baseline_values = baseline_categories.get(category, {})
            rows.append(
                {
                    "condition": condition,
                    "category": category,
                    "event_ordering": category in EVENT_ORDERING_CATEGORIES,
                    "n": value_or_missing(values, "n"),
                    "em": number_or_missing(values.get("em") if values else None),
                    "f1": number_or_missing(values.get("f1") if values else None),
                    "delta_em_vs_original_tiser": delta_or_missing(
                        values.get("em") if values else None,
                        baseline_values.get("em") if baseline_values else None,
                    ),
                    "delta_f1_vs_original_tiser": delta_or_missing(
                        values.get("f1") if values else None,
                        baseline_values.get("f1") if baseline_values else None,
                    ),
                }
            )
    return rows


def render_final_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Final Tennis Domain-Adaptation Results",
        "",
        "| Condition | Prompt Style | Tennis EM | Tennis F1 | Tennis Malformed Rate | Original TISER EM | Original TISER F1 | Forgetting Delta EM | Notes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {condition} | {prompt_style} | {tennis_em} | {tennis_f1} | "
            "{tennis_malformed_rate} | {original_tiser_em} | {original_tiser_f1} | "
            "{forgetting_delta_em} | {notes} |".format(
                condition=md_code(row["condition"]),
                prompt_style=md_value(row["prompt_style"]),
                tennis_em=fmt(row["tennis_em"]),
                tennis_f1=fmt(row["tennis_f1"]),
                tennis_malformed_rate=fmt(row["tennis_malformed_rate"]),
                original_tiser_em=fmt(row["original_tiser_em"]),
                original_tiser_f1=fmt(row["original_tiser_f1"]),
                forgetting_delta_em=fmt_delta(row["forgetting_delta_em"]),
                notes=escape_md(row["notes"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_forgetting(
    rows: list[dict[str, Any]], original_metrics: dict[str, dict[str, Any] | None]
) -> str:
    lines = [
        "# Original TISER Forgetting Analysis",
        "",
        "Forgetting delta is computed against `original_tiser` on the fixed original TISER sample. Negative values indicate degradation.",
        "",
        "| Condition | Original TISER EM | Original TISER F1 | Delta EM | Delta F1 | Metrics Path |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    baseline = extract_overall(original_metrics["original_tiser"])
    for row in rows:
        condition = row["condition"]
        overall = extract_overall(original_metrics[condition])
        lines.append(
            "| {condition} | {em} | {f1} | {delta_em} | {delta_f1} | {path} |".format(
                condition=md_code(condition),
                em=fmt(overall["em"]),
                f1=fmt(overall["f1"]),
                delta_em=fmt_delta(delta_or_missing(overall["em"], baseline["em"])),
                delta_f1=fmt_delta(delta_or_missing(overall["f1"], baseline["f1"])),
                path=md_value(metric_path(original_metrics[condition])),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_category_analysis(
    rows: list[dict[str, Any]], tennis_metrics: dict[str, dict[str, Any] | None]
) -> str:
    lines = [
        "# Tennis Category Analysis",
        "",
        "Event-ordering categories: "
        + ", ".join(md_code(category) for category in sorted(EVENT_ORDERING_CATEGORIES)),
        "",
        "## Per-Category Metrics",
        "",
        "| Condition | Category | Ordering | N | EM | F1 | Delta EM vs Original TISER | Delta F1 vs Original TISER |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {condition} | {category} | {ordering} | {n} | {em} | {f1} | {delta_em} | {delta_f1} |".format(
                condition=md_code(row["condition"]),
                category=md_code(row["category"]),
                ordering="yes" if row["event_ordering"] else "no",
                n=fmt(row["n"], decimals=0),
                em=fmt(row["em"]),
                f1=fmt(row["f1"]),
                delta_em=fmt_delta(row["delta_em_vs_original_tiser"]),
                delta_f1=fmt_delta(row["delta_f1_vs_original_tiser"]),
            )
        )

    lines.extend(["", "## Best and Worst Categories", ""])
    for condition in CONDITIONS:
        condition_rows = [row for row in rows if row["condition"] == condition and is_number(row["em"])]
        if not condition_rows:
            lines.append(f"- `{condition}`: MISSING")
            continue
        best = max(condition_rows, key=lambda row: (float(row["em"]), float(row["f1"])))
        worst = min(condition_rows, key=lambda row: (float(row["em"]), float(row["f1"])))
        lines.append(
            f"- `{condition}` best: `{best['category']}` EM={fmt(best['em'])}, F1={fmt(best['f1'])}; "
            f"worst: `{worst['category']}` EM={fmt(worst['em'])}, F1={fmt(worst['f1'])}"
        )

    lines.extend(["", "## Event-Ordering Highlight", ""])
    for condition in CONDITIONS:
        ordering = aggregate_category_group(tennis_metrics[condition], EVENT_ORDERING_CATEGORIES)
        other = aggregate_category_group(tennis_metrics[condition], None)
        lines.append(
            f"- `{condition}` ordering EM/F1: {fmt(ordering['em'])}/{fmt(ordering['f1'])}; "
            f"non-ordering EM/F1: {fmt(other['em'])}/{fmt(other['f1'])}"
        )
    lines.append("")
    return "\n".join(lines)


def aggregate_category_group(
    metrics: dict[str, Any] | None, categories: set[str] | None
) -> dict[str, Any]:
    if not metrics or not isinstance(metrics.get("per_category"), dict):
        return {"em": MISSING, "f1": MISSING}
    selected = []
    for category, values in metrics["per_category"].items():
        is_ordering = category in EVENT_ORDERING_CATEGORIES
        if (categories is not None and is_ordering) or (categories is None and not is_ordering):
            if is_number(values.get("n")) and is_number(values.get("em")) and is_number(values.get("f1")):
                selected.append(values)
    n_total = sum(int(row["n"]) for row in selected)
    if n_total == 0:
        return {"em": MISSING, "f1": MISSING}
    return {
        "em": sum(float(row["em"]) * int(row["n"]) for row in selected) / n_total,
        "f1": sum(float(row["f1"]) * int(row["n"]) for row in selected) / n_total,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, MISSING) for field in fieldnames})


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def metric_value(metrics: dict[str, Any] | None, key: str) -> Any:
    if metrics is None:
        return MISSING
    return metrics.get(key, MISSING)


def metric_path(metrics: dict[str, Any] | None) -> str:
    if metrics is None:
        return MISSING
    return str(metrics.get("_metrics_path", MISSING))


def value_or_missing(values: dict[str, Any] | None, key: str) -> Any:
    if not values:
        return MISSING
    return values.get(key, MISSING)


def number_or_missing(value: Any) -> Any:
    if value is None or value == MISSING:
        return MISSING
    return float(value) if is_number(value) else MISSING


def delta_or_missing(value: Any, baseline: Any) -> Any:
    if not is_number(value) or not is_number(baseline):
        return MISSING
    return float(value) - float(baseline)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def fmt(value: Any, decimals: int = 4) -> str:
    if not is_number(value):
        return MISSING
    if decimals == 0:
        return str(int(value))
    return f"{float(value):.{decimals}f}"


def fmt_delta(value: Any) -> str:
    if not is_number(value):
        return MISSING
    return f"{float(value):+.4f}"


def md_value(value: Any) -> str:
    if value in (None, "", MISSING):
        return MISSING
    return md_code(str(value))


def md_code(value: str) -> str:
    return f"`{escape_md(value)}`"


def escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


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
