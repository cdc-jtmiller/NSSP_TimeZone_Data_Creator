from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

PIPELINE = [
    "_01_install_requirements.py",
    "_02_fetch_geography.py",
    "_03_build_tz_table.py",
    "_04_compare_orig.py",
]


def run_script(script_name: str) -> None:
    script_path = SCRIPT_DIR / script_name

    if not script_path.exists():
        raise FileNotFoundError(f"Pipeline script not found: {script_path}")

    print("=" * 80)
    print(f"Running: {script_name}")
    print("=" * 80)

    cmd = [sys.executable, str(script_path)]
    subprocess.check_call(cmd)


def main() -> None:
    print("Starting TimeZone_Update pipeline...")

    for script_name in PIPELINE:
        run_script(script_name)

    print("=" * 80)
    print("Pipeline completed successfully.")
    print("=" * 80)


if __name__ == "__main__":
    main()
