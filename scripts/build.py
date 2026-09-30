"""Build the Windows executable.

Usage:
    python scripts\\build.py            # one-file exe
    python scripts\\build.py --onedir   # faster start, folder of files
    python scripts\\build.py --clean    # rebuild from scratch

PyInstaller is invoked through the spec file in packaging/ so the two never
drift apart.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "packaging" / "fileflow.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def ensure_requirements() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Run:")
        print("    python -m pip install pyinstaller")
        raise SystemExit(1) from None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the FileFlow executable.")
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build a folder of files instead of a single exe (faster startup)",
    )
    parser.add_argument("--clean", action="store_true", help="Remove build/ and dist/ first")
    parser.add_argument(
        "--console",
        action="store_true",
        help="Build a console build that prints tracebacks, for debugging a crash",
    )
    args = parser.parse_args()

    ensure_requirements()

    if args.clean:
        for path in (BUILD, DIST):
            if path.exists():
                print(f"removing {path}")
                shutil.rmtree(path)

    if not SPEC.exists():
        print(f"missing spec: {SPEC}")
        return 1

    # PyInstaller rejects --onefile/--onedir/--name when a spec file is
    # supplied, so the layout is chosen through the environment instead.
    env = dict(os.environ)
    env["FILEFLOW_ONEDIR"] = "1" if args.onedir else "0"
    env["FILEFLOW_CONSOLE"] = "1" if args.console else "0"

    command = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC),
        "--noconfirm",
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
    ]

    print("$", " ".join(command))
    started = time.perf_counter()

    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode != 0:
        print(f"\nbuild failed after {time.perf_counter() - started:.0f}s")
        return result.returncode

    elapsed = time.perf_counter() - started

    # PyInstaller can report success and still write nothing: a malformed spec
    # produces no executable at all without a non-zero exit code. Verify the
    # artifact rather than trusting the exit status.
    produced = sorted(DIST.rglob("FileFlow.exe"))
    if not produced:
        print(f"\nbuild reported success in {elapsed:.0f}s but produced no executable.")
        print(f"expected one under {DIST}")
        return 1

    print(f"\nbuild finished in {elapsed:.0f}s")
    for exe in produced:
        size_mb = exe.stat().st_size / 1024**2
        print(f"  {exe.relative_to(ROOT)}  ({size_mb:.1f} MB)")

        if size_mb < 1:
            print("    error: that is too small to contain the application")
            return 1

    print("\nThe executable is unsigned, so Windows SmartScreen will warn on first run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
