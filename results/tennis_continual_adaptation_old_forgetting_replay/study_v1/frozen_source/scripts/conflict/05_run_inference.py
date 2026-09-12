"""M5 CLI - execute a run-matrix cell (GPU).

Run the star cell first:
    python scripts/conflict/05_run_inference.py --model tiser --style tiser
then the surrounding cells (base x {tiser,standard}, tiser x standard).
"""

import argparse

from src.conflict.run import run_inference
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="M5: run a (model, style) inference cell.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--model", required=True, help="model tag in conflict.run.models (e.g. tiser|base)")
    parser.add_argument("--style", required=True, choices=["tiser", "standard"], help="prompt style")
    parser.add_argument("--limit", type=int, default=None, help="cap rows (smoke test)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_inference(cfg, args.model, args.style, limit=args.limit)


if __name__ == "__main__":
    main()
