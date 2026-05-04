from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    req_file = project_root / "utility" / "requirements.txt"

    if not req_file.exists():
        raise FileNotFoundError(f"requirements.txt not found at: {req_file}")

    print(f"Installing dependencies from: {req_file}")

    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Failed to install dependencies") from e

    print("Dependencies installed successfully.")


if __name__ == "__main__":
    main()
