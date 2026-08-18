import hashlib

from cloud.run_test_generation import _artifact_index


def test_final_test_artifact_index_contains_only_generated_tests_and_coverage(tmp_path):
    artifacts = tmp_path / "artifacts"
    generated = artifacts / "generated_tests" / "tests_candidate" / "test_parse.py"
    coverage = artifacts / "coverage" / "isort.json"
    ignored = artifacts / "generated_tests" / "notes.txt"
    generated.parent.mkdir(parents=True)
    coverage.parent.mkdir(parents=True)
    generated.write_text("def test_parse():\n    assert True\n", encoding="utf-8")
    coverage.write_text('{"totals": {}}', encoding="utf-8")
    ignored.write_text("not a test artifact", encoding="utf-8")

    result = _artifact_index(artifacts, [generated])

    assert [(entry["id"], entry["kind"], entry["path"]) for entry in result] == [
        ("generated-test-1", "generated_test", "generated_tests/tests_candidate/test_parse.py"),
        ("coverage-1", "coverage", "coverage/isort.json"),
    ]
    assert result[0]["content_type"] == "text/x-python"
    assert result[0]["size_bytes"] == len(generated.read_bytes())
    assert result[0]["sha256"] == hashlib.sha256(generated.read_bytes()).hexdigest()
    assert result[1]["content_type"] == "application/json"
    assert result[1]["size_bytes"] == len(coverage.read_bytes())
    assert result[1]["sha256"] == hashlib.sha256(coverage.read_bytes()).hexdigest()
