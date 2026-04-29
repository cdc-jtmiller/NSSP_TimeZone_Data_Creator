from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_script(script_name: str) -> None:
    project_root = Path(__file__).resolve().parent
    script_path = project_root / script_name
    cmd = [sys.executable, str(script_path)]
    subprocess.check_call(cmd)


def main() -> None:
    print("Step 1: Installing requirements from 'requirements.txt'...")
    run_script("install_requirements.py")

    print("Step 2: Fetching geography from 'fetch_geography.py'...")
    run_script("fetch_geography.py")

    print("Step 3: Building timezone table from 'build_tz_table.py'...")
    run_script("build_tz_table.py")


if __name__ == "__main__":
    main()
