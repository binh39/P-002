Tải python 3.11 về máy, sau đó tạo venv:

py -3.11 -m venv .venv

Sau đó active:

.\\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

Copy-Item .env.example .env

powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1

Sau đó paste nguyên đoạn dưới đây vào file .git/hooks/prepush:

#!C:/Program Files/Git/bin/bash.exe # Pre-push: sweep recent IDE transcripts, then submit AI logs.  bash scripts/\_pyrun.sh scripts/log\_antigravity.py --auto || true bash scripts/\_pyrun.sh scripts/log\_codex\_extension.py || true bash scripts/\_pyrun.sh scripts/submit\_log.py || true  exit 0

Sau đó lấy key phoenix paste vào env

2 lệnh để log và upload log lên web:

.\.venv\Scripts\python.exe .\scripts\log_codex_extension.py (không nên dùng nhiều vì bị mất log stop vs model)

.\.venv\Scripts\python.exe .\scripts\submit_log.py
