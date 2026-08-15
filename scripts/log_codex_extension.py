#!/usr/bin/env python3
"""Sweep Codex VS Code transcripts and append exact user prompts to ai-log."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

VN_TZ = timezone(timedelta(hours=7))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def existing_entries(log_file: Path) -> tuple[set[str], set[tuple[str, str]]]:
    ids = set()
    prompt_sources = set()
    if not log_file.exists():
        return ids, prompt_sources
    with log_file.open(encoding="utf-8-sig") as stream:
        for line in stream:
            try:
                entry = json.loads(line)
                entry_id = entry.get("entry_id")
                if entry_id:
                    ids.add(entry_id)
                if entry.get("tool") == "codex":
                    prompt_sources.add((
                        entry.get("prompt", "").strip(),
                        entry.get("session_id", ""),
                    ))
            except (json.JSONDecodeError, AttributeError):
                pass
    return ids, prompt_sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(git("rev-parse", "--show-toplevel") or ".").resolve()
    sessions = Path(os.environ.get(
        "CODEX_SESSIONS_DIR", str(Path.home() / ".codex" / "sessions")
    ))
    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_file = log_dir / "session.jsonl"
    logged, logged_prompt_sources = existing_entries(log_file)
    cutoff = None if args.all else datetime.now(timezone.utc) - timedelta(hours=args.hours)

    repo = Path(git("remote", "get-url", "origin")).stem or repo_root.name
    common = {
        "tool": "codex",
        "event": "UserPromptSubmit",
        "model": "",
        "repo": repo,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": git("rev-parse", "--short", "HEAD"),
        "student": git("config", "user.email"),
        "response_summary": "",
    }
    pending = []

    for transcript in sessions.rglob("rollout-*.jsonl"):
        try:
            if cutoff and datetime.fromtimestamp(
                transcript.stat().st_mtime, timezone.utc
            ) < cutoff:
                continue
            with transcript.open(encoding="utf-8") as stream:
                first = json.loads(next(stream))
                meta = first.get("payload", {})
                if meta.get("originator") != "codex_vscode":
                    continue
                if norm(meta.get("cwd", "")) != norm(str(repo_root)):
                    continue
                session_id = meta.get("session_id") or meta.get("id") or transcript.stem

                index = 0
                for line in stream:
                    item = json.loads(line)
                    payload = item.get("payload", {})
                    if item.get("type") != "event_msg" or payload.get("type") != "user_message":
                        continue
                    prompt = (payload.get("message") or "").strip()
                    if not prompt:
                        continue
                    index += 1
                    entry_id = f"codex-vscode-{session_id}-{index:05d}"
                    prompt_source = (prompt, session_id)
                    if entry_id in logged or prompt_source in logged_prompt_sources:
                        continue
                    ts_raw = item.get("timestamp", "")
                    try:
                        ts = datetime.fromisoformat(
                            ts_raw.replace("Z", "+00:00")
                        ).astimezone(VN_TZ).isoformat()
                    except ValueError:
                        ts = datetime.now(VN_TZ).isoformat()
                    pending.append({
                        **common,
                        "ts": ts,
                        "entry_id": entry_id,
                        "session_id": session_id,
                        "prompt": prompt[:1000],
                        "transcript_path": str(transcript),
                    })
        except (OSError, StopIteration, json.JSONDecodeError):
            continue

    pending.sort(key=lambda entry: entry["ts"])
    if args.dry_run:
        for entry in pending:
            print(json.dumps(entry, ensure_ascii=False))
        return
    if pending:
        log_dir.mkdir(exist_ok=True)
        with log_file.open("a", encoding="utf-8") as stream:
            for entry in pending:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[ai-log] Codex extension: added {len(pending)} prompt(s).")


if __name__ == "__main__":
    main()
