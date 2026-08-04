from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import run_harness_on


def main() -> None:
    parser = argparse.ArgumentParser(description="Run generated tests in the testgen sandbox")
    parser.add_argument("module_path", type=Path)
    parser.add_argument("test_file", type=Path)
    parser.add_argument("--no-mutation", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    result = run_harness_on(
        args.module_path,
        args.test_file.read_text(encoding="utf-8"),
        run_mutation=not args.no_mutation,
        timeout=args.timeout,
    )
    print(json.dumps(result.as_dict(), indent=2))
    raise SystemExit(0 if result.build_ok and result.pass_rate == 1.0 else 1)


if __name__ == "__main__":
    main()
