#!/usr/bin/env python3
"""Generate the report figures for the context--memory conflict extension.

The figures are derived only from committed scoring/statistics artifacts.  By
default, they are sized for one IEEE-style report column and written as both a
vector PDF and a 600 dpi PNG.

Run from anywhere inside or outside the repository:

    python scripts/report/generate_conflict_figures.py

Matplotlib is the only plotting dependency.  Install it with
``python -m pip install matplotlib`` if it is not already available.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIR = REPOSITORY_ROOT / "results" / "context_memory_conflict"
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "report" / "figures"

# One-column width for the IEEE two-column template used by the report.
COLUMN_WIDTH_IN = 3.45

CELL_ORDER = (
    ("base__standard", "base__tiser"),
    ("tiser__standard", "tiser__tiser"),
)
MODEL_LABELS = ("Base model", "TISER SFT")
PROMPT_LABELS = ("Standard", "TISER")

CLASS_ORDER = ("C1", "C2", "C3")
CLASS_NAMES = {
    "C1": "Date shift",
    "C2": "Entity swap",
    "C3": "Order reversal",
}

# Okabe--Ito blue and vermillion: distinguishable for common colour-vision
# deficiencies.  Hatching keeps the comparison legible in greyscale printing.
FAITHFUL_COLOUR = "#0072B2"
MEMORISED_COLOUR = "#D55E00"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing required result artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in result artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object in {path}")
    return value


def _number(mapping: dict[str, Any], key: str, *, source: Path) -> float:
    value = mapping.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SystemExit(f"Expected numeric field {key!r} in {source}")
    numeric = float(value)
    if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise SystemExit(f"Expected {key!r} in [0, 1] in {source}; got {value!r}")
    return numeric


def _load_results(results_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics_dir = results_dir / "scored"
    metrics: dict[str, Any] = {}
    for row in CELL_ORDER:
        for cell in row:
            path = metrics_dir / f"{cell}.metrics.json"
            payload = _read_json(path)
            overall = payload.get("overall")
            per_class = payload.get("per_class")
            if not isinstance(overall, dict) or not isinstance(per_class, dict):
                raise SystemExit(f"Missing overall/per_class result objects in {path}")
            metrics[cell] = payload

    stats_path = results_dir / "stats" / "stats.json"
    stats = _read_json(stats_path)
    stats_cells = stats.get("cells")
    if not isinstance(stats_cells, dict):
        raise SystemExit(f"Missing cells object in {stats_path}")

    # Prevent a figure from silently combining inconsistent scoring and CI files.
    for row in CELL_ORDER:
        for cell in row:
            score = _number(metrics[cell]["overall"], "faithful_em", source=metrics_dir)
            stats_cell = stats_cells.get(cell)
            if not isinstance(stats_cell, dict):
                raise SystemExit(f"Missing statistics for {cell!r} in {stats_path}")
            stats_score = _number(stats_cell, "faithful_em", source=stats_path)
            if not math.isclose(score, stats_score, rel_tol=0.0, abs_tol=1e-12):
                raise SystemExit(
                    f"Scoring/statistics mismatch for {cell}: {score} != {stats_score}"
                )

    return metrics, stats


def _configure_matplotlib() -> Any:
    try:
        import matplotlib
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Matplotlib is required. Install it with: python -m pip install matplotlib"
        ) from exc

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["STIXGeneral", "DejaVu Serif"],
            "font.size": 8.5,
            "axes.titlesize": 9.2,
            "axes.titleweight": "semibold",
            "axes.labelsize": 8.5,
            "xtick.labelsize": 8.2,
            "ytick.labelsize": 8.2,
            "legend.fontsize": 7.7,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": 0.7,
        }
    )
    return plt


def _save_figure(fig: Any, output_dir: Path, stem: str, dpi: int) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [output_dir / f"{stem}.pdf", output_dir / f"{stem}.png"]
    fig.savefig(paths[0], facecolor="white")
    fig.savefig(paths[1], dpi=dpi, facecolor="white")
    return paths


def _plot_run_matrix(
    plt: Any,
    metrics: dict[str, Any],
    stats: dict[str, Any],
    output_dir: Path,
    dpi: int,
) -> list[Path]:
    from matplotlib.colors import Normalize
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_IN, 2.35), layout="constrained")
    colour_map = plt.colormaps["cividis"]
    normalise = Normalize(vmin=0.0, vmax=1.0)

    stats_cells = stats["cells"]
    for row_index, row in enumerate(CELL_ORDER):
        for column_index, cell in enumerate(row):
            score = _number(
                metrics[cell]["overall"],
                "faithful_em",
                source=DEFAULT_RESULTS_DIR / "scored",
            )
            ci = stats_cells[cell].get("ci95")
            if (
                not isinstance(ci, list)
                or len(ci) != 2
                or any(not isinstance(value, (int, float)) for value in ci)
            ):
                raise SystemExit(f"Expected a two-element ci95 for {cell!r}")

            colour = colour_map(normalise(score))
            ax.add_patch(
                Rectangle(
                    (column_index - 0.5, row_index - 0.5),
                    1,
                    1,
                    facecolor=colour,
                    edgecolor="white",
                    linewidth=2.0,
                )
            )
            # Cividis is darkest at low values; switch text colour for contrast.
            text_colour = "white" if score < 0.50 else "#111111"
            ax.text(
                column_index,
                row_index - 0.06,
                f"{score:.3f}",
                ha="center",
                va="center",
                color=text_colour,
                fontsize=11.0,
                fontweight="bold",
            )
            ax.text(
                column_index,
                row_index + 0.21,
                f"[{float(ci[0]):.3f}, {float(ci[1]):.3f}]",
                ha="center",
                va="center",
                color=text_colour,
                fontsize=7.5,
            )

    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(1.5, -0.5)
    ax.set_aspect("equal")
    ax.set_xticks((0, 1), PROMPT_LABELS)
    ax.set_yticks((0, 1), MODEL_LABELS)
    ax.tick_params(axis="both", length=0, pad=4)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.set_xlabel("Prompt format", labelpad=5, fontweight="semibold")
    ax.set_ylabel("Model", labelpad=7, fontweight="semibold")
    ax.set_title("Context-faithful exact match", pad=7)
    ax.text(
        0.5,
        -0.16,
        "Value [95% bootstrap CI]; $n$ = 1,176 per cell",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=7.4,
        color="#333333",
    )
    for spine in ax.spines.values():
        spine.set_visible(False)

    paths = _save_figure(fig, output_dir, "conflict_run_matrix", dpi)
    plt.close(fig)
    return paths


def _plot_per_class(
    plt: Any,
    metrics: dict[str, Any],
    output_dir: Path,
    dpi: int,
) -> list[Path]:
    star_path = DEFAULT_RESULTS_DIR / "scored" / "tiser__tiser.metrics.json"
    star_classes = metrics["tiser__tiser"]["per_class"]
    faithful = [
        _number(star_classes[class_name], "faithful_em", source=star_path)
        for class_name in CLASS_ORDER
    ]
    memorised = [
        _number(star_classes[class_name], "memorised_em", source=star_path)
        for class_name in CLASS_ORDER
    ]

    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_IN, 2.70))
    # Reserve fixed title/legend and category-label bands.  This is more stable
    # than allowing a tight-bounding-box export to change the intended width.
    fig.subplots_adjust(left=0.17, right=0.98, bottom=0.23, top=0.72)
    positions = list(range(len(CLASS_ORDER)))
    width = 0.34
    faithful_bars = ax.bar(
        [position - width / 2 for position in positions],
        faithful,
        width,
        label="Context-faithful EM",
        color=FAITHFUL_COLOUR,
        edgecolor="#222222",
        linewidth=0.5,
        hatch="///",
    )
    memorised_bars = ax.bar(
        [position + width / 2 for position in positions],
        memorised,
        width,
        label="Memorised-answer EM",
        color=MEMORISED_COLOUR,
        edgecolor="#222222",
        linewidth=0.5,
        hatch="\\\\",
    )

    for bars in (faithful_bars, memorised_bars):
        ax.bar_label(
            bars,
            labels=[f"{bar.get_height():.3f}" for bar in bars],
            padding=2,
            fontsize=7.5,
        )

    class_labels = []
    for class_name in CLASS_ORDER:
        count = star_classes[class_name].get("n")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise SystemExit(f"Expected a positive class count for {class_name!r}")
        class_labels.append(f"{CLASS_NAMES[class_name]}\n{class_name} ($n$={count})")
    ax.set_xticks(positions, class_labels)
    ax.set_ylim(0.0, 1.09)
    ax.set_yticks((0.0, 0.25, 0.5, 0.75, 1.0))
    ax.set_ylabel("Exact match")
    fig.suptitle("TISER SFT + TISER prompt", y=0.97, fontsize=9.2, fontweight="bold")
    ax.grid(axis="y", color="#D7D7D7", linewidth=0.6, linestyle="--")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.88),
        ncols=2,
        frameon=False,
        handlelength=1.5,
        columnspacing=0.9,
    )

    paths = _save_figure(fig, output_dir, "conflict_per_class", dpi)
    plt.close(fig)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="context-memory conflict result directory (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="directory for generated PDF/PNG files (default: %(default)s)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=600,
        help="PNG resolution in dots per inch (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dpi < 300:
        raise SystemExit("--dpi must be at least 300 for publication output")

    results_dir = args.results_dir.resolve()
    output_dir = args.output_dir.resolve()
    metrics, stats = _load_results(results_dir)
    plt = _configure_matplotlib()

    written = []
    written.extend(_plot_run_matrix(plt, metrics, stats, output_dir, args.dpi))
    written.extend(_plot_per_class(plt, metrics, output_dir, args.dpi))
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
