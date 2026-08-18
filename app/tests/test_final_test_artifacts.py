from backend.modules.experiments.service import _validated_final_test_artifact_objects


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
