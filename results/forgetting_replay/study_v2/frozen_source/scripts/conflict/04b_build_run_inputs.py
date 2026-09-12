"""M4 CLI - build run-input prompts per style (CPU)."""

import argparse

from src.conflict.prompts import build_run_inputs
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="M4: build per-style run-input prompts.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--styles", default=None,
                        help="comma-separated styles to build (e.g. 'tiser' or 'tiser,standard'); "
                             "overrides conflict.prompts.styles")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.styles is not None:
        cfg.conflict.prompts.styles = [s.strip() for s in args.styles.split(",") if s.strip()]

    build_run_inputs(cfg)


if __name__ == "__main__":
    main()
