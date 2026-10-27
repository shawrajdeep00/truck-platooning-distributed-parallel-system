"""Run every suite, including after failures, with a timeout per C executable."""

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
C_TESTS = (
    "heartbeat_test",
    "test_matrix_clock",
    "test_cruise_control",
    "test_intruder",
    "test_leader_integration",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suites", nargs="*", choices=(*C_TESTS, "python"))
    args = parser.parse_args()
    results = []
    for name in args.suites or (*C_TESTS, "python"):
        command = (
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
            if name == "python" else [str(ROOT / "bin" / name)]
        )
        print(f"\n=== {name} ===", flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, timeout=45, check=False)
            passed = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"FAILED: {exc}", file=sys.stderr)
            passed = False
        results.append((name, passed))
    print("\nSuite results:", flush=True)
    for name, passed in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name}", flush=True)
    return 0 if all(passed for _, passed in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
