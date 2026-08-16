from __future__ import annotations

import json
import os
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import dspy
from dotenv import load_dotenv

from src.optimization.gepa import CoverUpPromptAdapter
from src.optimization.models import ExperimentConfig, SymbolTarget
from src.optimization.prompts import baseline_bundle
from src.optimization.runner import CoverUpExperimentRunner


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
    # LiteLLM's static model catalog can lag newly configured provider models.
    # The actual tool-call response below is the authoritative capability test.
    advertised_function_calling = lm.supports_function_calling

    baseline = baseline_bundle()
    synthetic_episode = {
        "Inputs": {
            "target": "pkg/module.py::target",
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
    with tempfile.TemporaryDirectory(
        prefix="native-reflection-smoke-", dir=Path.cwd()
    ) as temporary:
        root = Path(temporary)
        package_dir = root / "sample_repo" / "pkg"
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "module.py").write_text(
            "def target(value):\n    return value + 1\n", encoding="utf-8"
        )
        candidate_dir = root / "artifacts" / "candidates"
        target = SymbolTarget(
            "project", "pkg/module.py", "target", "train"
        )
        adapter = CoverUpPromptAdapter(
            runner=CoverUpExperimentRunner(ExperimentConfig(
                project_root=root,
                package_dir=package_dir,
                tests_dir=root / "sample_repo" / "tests",
                artifacts_dir=root / "artifacts",
                coverup_model="unused-by-reflection-smoke",
                repeat_tests=1,
            )),
            candidate_dir=candidate_dir,
            targets_by_split={"train": [target]},
            baseline=baseline,
            reflection_lm=lm,
        )
        captured_log = StringIO()
        with redirect_stdout(captured_log):
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
        experiment_records = [
            json.loads(line)
            for line in (candidate_dir / "optimizer_test_experiments.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        if not any(record["success"] for record in experiment_records):
            raise RuntimeError("Optimizer did not prove a successful test experiment")
        print(json.dumps({
            "model": model,
            "advertised_function_calling": advertised_function_calling,
            "native_function_call_verified": True,
            "selection": decision["selection"],
            "changed_components": decision["changed_components"],
            "status": decision["status"],
            "optimizer_calls": decision["optimizer_calls"],
            "successful_experiment_ids": decision["successful_experiment_ids"],
            "replacement_lengths": {
                component: len(proposals[component])
                for component in decision["changed_components"]
            },
        }, indent=2))


if __name__ == "__main__":
    main()
