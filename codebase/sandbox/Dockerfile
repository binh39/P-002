FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.13 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --python /usr/local/bin/python3.12

FROM python:3.12-slim

WORKDIR /workspace
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/opt/promptopt"

RUN useradd --create-home runner
COPY src/coverup /opt/promptopt/coverup
COPY codebase/sandbox/runner_entry.py /opt/promptopt/runner_entry.py
COPY codebase/sandbox/cloud_job_entry.py /opt/promptopt/cloud_job_entry.py
COPY codebase/src/modules/experiments/traces.py /opt/promptopt/traces.py

USER runner
CMD ["python", "/opt/promptopt/cloud_job_entry.py"]
