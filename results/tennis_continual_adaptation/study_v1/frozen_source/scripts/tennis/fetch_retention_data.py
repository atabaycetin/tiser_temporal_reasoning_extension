"""Fetch the exact original-TISER revision used by the conditional study."""
from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.data.dataset import _load_records
from src.experiment.artifacts import read, sha256, write
from src.experiment.study import PINNED_DATA_REVISION

EXPECTED_FILES = {
    "TISER_train.json": {"sha256": "9976951c0a280dfec54232c0f99e51abe688c8d3241528095238f5678741daea",
                         "n": 54488, "bytes": 208492422},
    "TISER_test.json": {"sha256": "e4e6c76fefcd86a9adfc0f588237cf8dc9a5d2366f59b61c765f1ef5b1d04a91",
                        "n": 22014, "bytes": 88027332},
}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default="data")
    args = p.parse_args(argv)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    source = output / "TISER_source.json"
    previous = read(source) if source.exists() else None
    if previous and previous["revision"] != PINNED_DATA_REVISION:
        raise ValueError("Existing source manifest has a different revision")
    files = {}
    for name in ("TISER_train.json", "TISER_test.json"):
        path = output / name
        url = f"https://media.githubusercontent.com/media/amazon-science/TISER/{PINNED_DATA_REVISION}/data/{name}"
        if path.exists():
            if sha256(path) != EXPECTED_FILES[name]["sha256"]:
                raise ValueError(f"Existing data differs from the pinned release: {path}")
        else:
            temporary = path.with_suffix(".download")
            with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            _load_records(str(temporary))
            temporary.replace(path)
        observed = {"sha256": sha256(path), "n": len(_load_records(str(path))), "bytes": path.stat().st_size}
        if observed != EXPECTED_FILES[name]:
            raise ValueError(f"Downloaded data differs from the pinned release: {path}")
        files[name] = {"url": url, **observed}
        # Save after each completed file so a failed second download can resume.
        write(source, {"repository": "https://github.com/amazon-science/TISER", "revision": PINNED_DATA_REVISION, "files": files})
    print(f"Verified original TISER revision {PINNED_DATA_REVISION}")


if __name__ == "__main__":
    main()
