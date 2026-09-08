"""M6 CLI - parse traces + score faithfulness / memorisation / guardrail EM (CPU)."""

import argparse

from src.conflict.score import score
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="M6: score a (model, style) generation file.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--model", required=True, help="model tag (matches the generations file)")
    parser.add_argument("--style", required=True, choices=["tiser", "standard"], help="prompt style")
    args = parser.parse_args()

    cfg = load_config(args.config)
    score(cfg, args.model, args.style)


if __name__ == "__main__":
    main()
