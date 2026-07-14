from __future__ import annotations

import subprocess


def main() -> int:
    return subprocess.run(
        ["poetry", "run", "pytest", "-q"],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
