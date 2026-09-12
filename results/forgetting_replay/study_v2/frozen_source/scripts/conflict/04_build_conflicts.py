"""M3 CLI - deterministic perturbation engine (CPU, seeded)."""

import argparse

from src.conflict.perturb import build_conflicts
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="M3: build the labelled conflict set.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--classes", default=None,
                        help="comma-separated subset to build (e.g. 'C2' or 'C1,C2,C3'); "
                             "overrides conflict.perturb.classes (D-NCLASS 1-class mode)")
    parser.add_argument("--control-size", type=int, default=None,
                        help="override conflict.perturb.control_size")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.classes is not None:
        cfg.conflict.perturb.classes = [c.strip() for c in args.classes.split(",") if c.strip()]
    if args.control_size is not None:
        cfg.conflict.perturb.control_size = args.control_size

    build_conflicts(cfg)


if __name__ == "__main__":
    main()
