from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import dspy
from dotenv import load_dotenv

from src.optimization.gepa import CoverUpPromptAdapter
from src.optimization.prompts import baseline_bundle


def main() -> None:
    load_dotenv(Path.cwd() / ".env")
    model = os.environ.get("OPTIMIZE_MODEL", "").strip()
    if not model:
        raise RuntimeError("OPTIMIZE_MODEL is not configured")
    lm = dspy.LM(
        model,
        max_tokens=8192,
        temperature=0.2,
        cache=False,
    )
    if not lm.supports_function_calling:
        raise RuntimeError(f"Configured model does not support function calling: {model}")

    baseline = baseline_bundle()
    synthetic_episode = {
        "Inputs": {
            "target": "synthetic.py::target",
            "source_context": "1: def target(value):\n2:     return value + 1",
        },
        "Generated Outputs": {
            "candidate_score": 0.2,
            "parent_score": 0.2,
            "comparison_outcome": "tied",
            "execution_episodes": [{
                "initial_attempts": [{
                    "component": "initial",
                    "outcome": "test_error",
                    "generated_test": "def test_target(): assert missing_name",
                    "execution_error": "NameError: missing_name",
                }],
                "repair_transitions": [{
                    "failing_test": "def test_target(): assert missing_name",
                    "error": "NameError: missing_name",
                    "repaired_test": "def test_target(): assert True",
                    "outcome": "no_coverage_gain_unrepairable",
                }],
            }],
        },
        "Feedback": "The initial test failed and its repair produced no coverage gain.",
    }
    with tempfile.TemporaryDirectory(prefix="native-reflection-smoke-") as temporary:
        candidate_dir = Path(temporary)
        adapter = CoverUpPromptAdapter(
            runner=SimpleNamespace(),
            candidate_dir=candidate_dir,
            targets_by_split={},
            baseline=baseline,
            reflection_lm=lm,
        )
        proposals = adapter.propose_new_texts(
            baseline.as_candidate(),
            {
                "initial": [synthetic_episode],
                "error": [synthetic_episode],
            },
            ["initial", "error"],
        )
        decision = json.loads(
            (candidate_dir / "reflection_decisions.jsonl").read_text(encoding="utf-8")
        )
        if decision["status"] != "accepted" or not decision["changed_components"]:
            raise RuntimeError(f"Native reflection smoke was not accepted: {decision}")
        print(json.dumps({
            "model": model,
            "supports_function_calling": lm.supports_function_calling,
            "selection": decision["selection"],
            "changed_components": decision["changed_components"],
            "status": decision["status"],
            "replacement_lengths": {
                component: len(proposals[component])
                for component in decision["changed_components"]
            },
        }, indent=2))


if __name__ == "__main__":
    main()
