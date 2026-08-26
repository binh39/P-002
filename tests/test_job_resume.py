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
