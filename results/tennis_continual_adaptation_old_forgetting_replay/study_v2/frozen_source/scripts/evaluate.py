import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.eval.run_eval import run_eval
from src.utils.config import REPO_ROOT, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the trained TISER adapter.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--adapter-dir", default=None, help="defaults to model/<run_name>/adapter")
    parser.add_argument("--test-file", default=None, help="override paths.test_file")
    parser.add_argument("--run-name", default=None, help="override the output run name")
    parser.add_argument("--output-dir", default=None, help="override the output parent directory")
    parser.add_argument("--max-samples-per-split", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--manifest", help="Require this exact evaluation_spec.json")
    parser.add_argument("--eval-engine", choices=["hf", "vllm"], default=None,
                        help="generation backend; overrides eval.engine (default hf = frozen-baseline repro)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.test_file is not None:
        path = Path(args.test_file)
        cfg.paths.test_file = str(path if path.is_absolute() else Path(REPO_ROOT) / path)
    if args.run_name is not None:
        cfg.run_name = args.run_name
    if args.output_dir is not None:
        path = Path(args.output_dir)
        cfg.paths.output_dir = str(path if path.is_absolute() else Path(REPO_ROOT) / path)
    if args.max_samples_per_split is not None:
        cfg.eval.max_samples_per_split = args.max_samples_per_split
    if args.eval_engine is not None:
        cfg.eval.engine = args.eval_engine

    run_eval(cfg, adapter_dir=args.adapter_dir, resume=args.resume, manifest=args.manifest)


if __name__ == "__main__":
    main()
