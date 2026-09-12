import argparse

from src.data.fetch import ensure_data
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and validate the TISER datasets.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    ensure_data(cfg)


if __name__ == "__main__":
    main()
