import json
import os
import sys
from pathlib import Path

from cloud import run_job


def test_gepa_image_contains_pause_signal_module():
    dockerfile = (Path(__file__).parents[1] / "cloud" / "Dockerfile.web").read_text(encoding="utf-8")
    assert "COPY src/promptopt_pause.py ./src/promptopt_pause.py" in dockerfile


def test_job_publishes_resumable_pause_checkpoint(monkeypatch, tmp_path):
    uploaded: dict = {}

    def run(_command):
        pause_path = Path(os.environ["PROMPTOPT_PAUSE_FILE"])
        pause_path.parent.mkdir(parents=True, exist_ok=True)
        pause_path.write_text(
            json.dumps({"reason": "rate_limited", "message": "HTTP 429"}),
            encoding="utf-8",
        )
        (pause_path.parent / "gepa_direct_logs" / "digest").mkdir(parents=True)
        (pause_path.parent / "gepa_direct_logs" / "digest" / "gepa_state.bin").write_bytes(b"state")
        return 1, "rate limited"

    def upload(_bucket, _prefix, local_dir):
        uploaded.update(json.loads((local_dir / "job_result.json").read_text(encoding="utf-8")))
        assert (local_dir / "gepa_direct_logs" / "digest" / "gepa_state.bin").read_bytes() == b"state"

    monkeypatch.setattr(run_job, "_run_cli", run)
    monkeypatch.setattr(run_job, "_upload_dir", upload)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_job",
            "--bucket",
            "bucket",
            "--artifacts-name",
            "run",
            "--local-root",
            str(tmp_path),
            "--",
            "optimize",
        ],
    )

    assert run_job.main() == 0
    assert uploaded["status"] == "paused"
    assert uploaded["pause"]["reason"] == "rate_limited"


def test_job_restores_checkpoint_before_resume(monkeypatch, tmp_path):
    observed = {}

    def download(_bucket, prefix, destination):
        observed["source"] = prefix
        state = destination / "gepa_direct_logs" / "digest" / "gepa_state.bin"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_bytes(b"restored")
        return 1

    def run(command):
        artifacts = Path(command[command.index("--artifacts-dir") + 1])
        assert (artifacts / "gepa_direct_logs" / "digest" / "gepa_state.bin").read_bytes() == b"restored"
        assert os.environ["PROMPTOPT_RESUMING"] == "1"
        for relative in (
            "optimized_program.json",
            "prompts/gepa_proposed.json",
            "prompts/gepa_optimized.json",
            "final_validation.json",
        ):
            path = artifacts / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        return 0, None

    monkeypatch.setattr(run_job, "_download_dir", download)
    monkeypatch.setattr(run_job, "_run_cli", run)
    monkeypatch.setattr(run_job, "_upload_dir", lambda *_args: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_job",
            "--bucket",
            "bucket",
            "--artifacts-name",
            "new-run",
            "--resume-artifacts-name",
            "old-run",
            "--local-root",
            str(tmp_path),
            "--",
            "optimize",
        ],
    )

    assert run_job.main() == 0
    assert observed["source"] == "old-run"


def test_dynamic_resume_keeps_remote_worker_prefix(monkeypatch, tmp_path):
    observed = {}
    sample_root = tmp_path / "samples"
    (sample_root / "isort" / "isort").mkdir(parents=True)
    (sample_root / "isort" / "tests").mkdir(parents=True)
    (sample_root / "isort" / "isort" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (sample_root / "isort" / "tests" / "test_value.py").write_text(
        "from isort import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 3,
        "projects": [
            {
                "kind": "sample",
                "project": "isort",
                "sample_slug": "isort",
                "source_directory": "isort",
                "test_directory": "tests",
                "runtime_digest": "sample:isort",
            }
        ],
    }

    def download_object(_bucket, object_name, destination):
        destination = Path(destination)
        if object_name.endswith("dataset.jsonl"):
            destination.write_text('{"project":"isort"}\n', encoding="utf-8")
        elif object_name.endswith("prompt.json"):
            destination.write_text("{}", encoding="utf-8")
        elif object_name.endswith("projects.json"):
            destination.write_text(json.dumps(manifest), encoding="utf-8")
        else:
            raise AssertionError(object_name)

    def run(command):
        observed["prefix"] = os.environ["PROMPTOPT_EVALUATION_PREFIX"]
        artifacts = Path(command[command.index("--artifacts-dir") + 1])
        for relative in (
            "optimized_program.json",
            "prompts/gepa_proposed.json",
            "prompts/gepa_optimized.json",
            "final_validation.json",
        ):
            path = artifacts / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        return 0, None

    monkeypatch.setattr(run_job, "_download_object", download_object)
    monkeypatch.setattr(run_job, "_download_dir", lambda *_args: 0)
    monkeypatch.setattr(run_job, "_upload_dir", lambda *_args: None)
    monkeypatch.setattr(run_job, "_run_cli", run)
    monkeypatch.setenv("PROMPTOPT_EVALUATION_JOB_SAMPLE", "projects/p/locations/r/jobs/eval-sample")
    monkeypatch.setenv("PROMPTOPT_SAMPLE_RUNTIME_IMAGE", "image@sha256:one")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_job",
            "--bucket",
            "bucket",
            "--artifacts-name",
            "new-run",
            "--resume-artifacts-name",
            "old-run",
            "--sample-repos-dir",
            str(sample_root),
            "--dataset-object",
            "inputs/dataset.jsonl",
            "--prompt-object",
            "inputs/prompt.json",
            "--project-manifest-object",
            "inputs/projects.json",
        ],
    )

    assert run_job.main() == 0
    assert observed["prefix"] == "old-run"
