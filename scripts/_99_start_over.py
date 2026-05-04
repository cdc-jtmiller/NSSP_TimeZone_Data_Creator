from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
VENV_DIR = PROJECT_ROOT / ".venv"

# Toggle this if you want full environment reset
DELETE_VENV = False


def clear_directory(path: Path) -> None:
    if not path.exists():
        return

    print(f"Clearing directory: {path}")
    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)


def uninstall_packages() -> None:
    print("Uninstalling project packages from virtual environment...")

    packages = [
        "pandas",
        "geopandas",
        "requests",
        "shapely",
        "pyogrio",
        "pyproj",
        "tzdata",
        "fiona",
        "psutil",
    ]

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "uninstall",
        "-y",
        *packages,
    ]

    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"Warning: could not uninstall packages: {e}")


def delete_venv() -> None:
    if not VENV_DIR.exists():
        return

    print(f"Deleting virtual environment: {VENV_DIR}")
    shutil.rmtree(VENV_DIR, ignore_errors=True)


def main() -> None:
    print("Starting full reset...")

    clear_directory(DATA_DIR)
    clear_directory(OUTPUT_DIR)

    if DELETE_VENV:
        delete_venv()
    else:
        uninstall_packages()

    print("Reset complete.")


if __name__ == "__main__":
    main()
