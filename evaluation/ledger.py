from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def holdout_digest(examples: list[Any]) -> str:
    identities = [
        {
            "id": getattr(example, "example_id", str(index)),
            "focal_code": example.focal_code,
        }
        for index, example in enumerate(examples)
    ]
    serialized = json.dumps(identities, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


class HoldoutLedger:
    """Prevent accidental repeated use of the locked holdout by one baseline."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _read(self) -> dict:
        if not self.path.exists():
            return {"runs": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def assert_available(self, baseline: str, digest: str) -> None:
        existing = self._read()["runs"].get(baseline)
        if existing is not None:
            raise RuntimeError(
                f"Holdout baseline {baseline!r} was already evaluated "
                f"with digest {existing['holdout_digest']}"
            )

    def complete(self, baseline: str, digest: str, result_file: str | Path) -> None:
        data = self._read()
        data["runs"][baseline] = {
            "holdout_digest": digest,
            "result_file": str(result_file),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.path)
