from backend.modules.experiments.schemas import TestGenerationMetrics as GenerationMetrics
from backend.modules.experiments.service import _validated_final_test_artifact_objects


def test_final_test_metrics_accept_worker_target_coverage_counts():
    metrics = GenerationMetrics.model_validate(
        {
            "target_statement_coverage": 367 / 662,
            "target_branch_coverage": 255 / 472,
            "target_covered_statements": 367,
            "target_statement_count": 662,
            "target_covered_branches": 255,
            "target_branch_count": 472,
            "target_count": 20,
            "completed_target_count": 20,
            "failed_target_count": 0,
            "test_file_count": 12,
            "test_count": 88,
        }
    )

    assert metrics.target_covered_statements == 367
    assert metrics.target_statement_count == 662
    assert metrics.target_covered_branches == 255
    assert metrics.target_branch_count == 472


def test_final_test_artifact_index_only_maps_safe_generated_source_and_coverage_paths():
    objects = _validated_final_test_artifact_objects(
        "runner-jobs/final-test-generation/run-1/artifacts",
        {
            "files": [
                {
                    "id": "generated-test-1",
                    "kind": "generated_test",
                    "path": "generated_tests/final/test_parse.py",
                },
                {"id": "coverage-1", "kind": "coverage", "path": "coverage/isort.json"},
                {"id": "source-1", "kind": "source", "path": "source/sample_isort/isort/parse.py"},
                {"id": "unsafe-1", "kind": "generated_test", "path": "../private/key.py"},
                {"id": "unknown-1", "kind": "source", "path": "source/parse.py"},
            ]
        },
    )

    assert objects == {
        "manifest": "runner-jobs/final-test-generation/run-1/artifacts/test_generation_result.json",
        "suite_zip": "runner-jobs/final-test-generation/run-1/artifacts/generated_tests.zip",
        "file-generated-test-1": "runner-jobs/final-test-generation/run-1/artifacts/generated_tests/final/test_parse.py",
        "file-coverage-1": "runner-jobs/final-test-generation/run-1/artifacts/coverage/isort.json",
        "file-source-1": "runner-jobs/final-test-generation/run-1/artifacts/source/sample_isort/isort/parse.py",
    }
