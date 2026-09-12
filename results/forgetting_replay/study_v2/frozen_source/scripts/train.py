import argparse

from src.train.trainer import run_training
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the TISER QLoRA baseline.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--subset", type=int, default=None, help="cap training examples")
    parser.add_argument("--epochs", type=float, default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.subset is not None:
        cfg.train.subset_size = args.subset
    if args.epochs is not None:
        cfg.train.num_epochs = args.epochs
    if args.output_dir is not None:
        cfg.paths.output_dir = args.output_dir

    run_training(cfg)


if __name__ == "__main__":
    main()
