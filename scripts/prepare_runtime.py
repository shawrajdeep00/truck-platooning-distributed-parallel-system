"""Prepare the demo directory; reset only named demo files when requested."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(directory, reset=False):
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("leader.log", "follower1.log", "follower2.log", "follower3.log"):
        path = directory / name
        if reset or not path.exists():
            path.write_text("", encoding="utf-8")
    for fid in range(1, 4):
        path = directory / f"intruder_{fid}.txt"
        if reset or not path.exists():
            path.write_text(f"0 {fid} 0 0 0 0 0\n", encoding="utf-8")
    if reset:
        for name in ("latest.json", "latest.tmp", "stream.csv"):
            (directory / name).unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Clear named runtime files. Stop all demo processes first.")
    args = parser.parse_args()
    prepare(ROOT / "runtime", reset=args.reset)
    print(f"Runtime ready: {ROOT / 'runtime'}")
