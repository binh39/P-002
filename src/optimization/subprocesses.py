from __future__ import annotations

import codecs
import os
import subprocess
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path

_OUTPUT_LOCK = threading.Lock()


def run_streamed(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    label: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a child process while forwarding and retaining output immediately."""
    child_env = dict(os.environ if env is None else env)
    child_env["PYTHONUNBUFFERED"] = "1"
    if label:
        with _OUTPUT_LOCK:
            print(f"==> [{label}] started", flush=True)
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    if process.stdout is None:  # pragma: no cover - guaranteed by PIPE
        raise RuntimeError("Streaming subprocess has no stdout pipe")

    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    output: list[str] = []
    try:
        while chunk := os.read(process.stdout.fileno(), 4096):
            text = decoder.decode(chunk)
            if text:
                output.append(text)
                with _OUTPUT_LOCK:
                    print(text, end="", flush=True)
        final_text = decoder.decode(b"", final=True)
        if final_text:
            output.append(final_text)
            with _OUTPUT_LOCK:
                print(final_text, end="", flush=True)
    except BaseException:
        process.terminate()
        process.wait()
        raise
    finally:
        process.stdout.close()
    returncode = process.wait()
    if label:
        with _OUTPUT_LOCK:
            print(f"==> [{label}] finished with exit code {returncode}", flush=True)
    return subprocess.CompletedProcess(
        args=list(command),
        returncode=returncode,
        stdout="".join(output),
        stderr=None,
    )
