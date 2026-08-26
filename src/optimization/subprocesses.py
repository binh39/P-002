from __future__ import annotations

import codecs
import os
import signal
import subprocess
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path

_OUTPUT_LOCK = threading.Lock()
_TIMEOUT_EXIT_CODE = 124


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Stop a streamed process and its descendants without waiting forever."""
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_streamed(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    label: str | None = None,
    echo: bool = True,
    announce: bool | None = None,
    timeout: float | None = None,
    echo_prefixes: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    """Run a child process, retaining output and optionally echoing it live."""
    if timeout is not None and timeout <= 0:
        raise ValueError("timeout must be positive")
    child_env = dict(os.environ if env is None else env)
    child_env["PYTHONUNBUFFERED"] = "1"
    show_lifecycle = echo if announce is None else announce
    if show_lifecycle and label:
        with _OUTPUT_LOCK:
            suffix = f" (timeout {timeout:g}s)" if timeout is not None else ""
            print(f"==> [{label}] started{suffix}", flush=True)
    popen_options = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        **popen_options,
    )
    if process.stdout is None:  # pragma: no cover - guaranteed by PIPE
        raise RuntimeError("Streaming subprocess has no stdout pipe")

    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    output: list[str] = []
    selected_line_buffer = ""
    finished = threading.Event()
    timed_out = threading.Event()

    def enforce_timeout() -> None:
        assert timeout is not None
        if not finished.wait(timeout):
            timed_out.set()
            _terminate_process_tree(process)

    watchdog = None
    if timeout is not None:
        watchdog = threading.Thread(target=enforce_timeout, name="subprocess-timeout", daemon=True)
        watchdog.start()
    try:
        while chunk := os.read(process.stdout.fileno(), 4096):
            text = decoder.decode(chunk)
            if text:
                output.append(text)
                if echo:
                    with _OUTPUT_LOCK:
                        print(text, end="", flush=True)
                elif echo_prefixes:
                    selected_line_buffer += text
                    lines = selected_line_buffer.splitlines(keepends=True)
                    selected_line_buffer = ""
                    if lines and not lines[-1].endswith(("\n", "\r")):
                        selected_line_buffer = lines.pop()
                    selected = "".join(
                        line for line in lines if line.startswith(tuple(echo_prefixes))
                    )
                    if selected:
                        with _OUTPUT_LOCK:
                            print(selected, end="", flush=True)
        final_text = decoder.decode(b"", final=True)
        if final_text:
            output.append(final_text)
            if echo:
                with _OUTPUT_LOCK:
                    print(final_text, end="", flush=True)
            elif echo_prefixes:
                selected_line_buffer += final_text
        if not echo and echo_prefixes and selected_line_buffer.startswith(tuple(echo_prefixes)):
            with _OUTPUT_LOCK:
                print(selected_line_buffer, end="", flush=True)
    except BaseException:
        _terminate_process_tree(process)
        process.wait()
        raise
    finally:
        finished.set()
        process.stdout.close()
        if watchdog is not None:
            watchdog.join(timeout=2)
    returncode = process.wait()
    if timed_out.is_set():
        returncode = _TIMEOUT_EXIT_CODE
        timeout_message = f"\nProcess timed out after {timeout:g} seconds.\n"
        output.append(timeout_message)
        if show_lifecycle:
            with _OUTPUT_LOCK:
                print(timeout_message, end="", flush=True)
    if show_lifecycle and label:
        with _OUTPUT_LOCK:
            print(f"==> [{label}] finished with exit code {returncode}", flush=True)
    return subprocess.CompletedProcess(
        args=list(command),
        returncode=returncode,
        stdout="".join(output),
        stderr=None,
    )
