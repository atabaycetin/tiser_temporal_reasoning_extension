"""M2 CLI - eligibility filter + GO/NO-GO yield gate (CPU)."""

import argparse

from src.conflict.eligibility import filter_eligible
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="M2: eligibility filter + yield gate.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--primary-model", default=None, help="override eligibility.primary_model")
    parser.add_argument("--agreement-min", type=float, default=None, help="override eligibility.agreement_min")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.primary_model is not None:
        cfg.conflict.eligibility.primary_model = args.primary_model
    if args.agreement_min is not None:
        cfg.conflict.eligibility.agreement_min = args.agreement_min

    filter_eligible(cfg)


if __name__ == "__main__":
    main()
