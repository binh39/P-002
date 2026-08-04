from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GeneratedTest:
    test_code: str
    cost_usd: float = 0.0
    latency_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class BaselineEvaluation:
    name: str
    build_rate: float
    pass_rate: float
    statement_coverage: float
    branch_coverage: float
    mutation_score: float
    cost_usd: float
    latency_seconds: float
    holdout_digest: str
    per_example: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.as_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> BaselineEvaluation:
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))
