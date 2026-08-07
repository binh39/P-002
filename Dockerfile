# ---- Stage 1: Build ----
FROM python:3.12-slim AS builder

# uv matches the local toolchain (uv 0.9.13)
COPY --from=ghcr.io/astral-sh/uv:0.9.13 /uv /uvx /bin/

WORKDIR /app

# Sync dependencies from uv.lock (same versions as the local venv)
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --python /usr/local/bin/python3.12

# ---- Stage 2: Production ----
FROM python:3.12-slim

WORKDIR /app

# Copy the uv-managed venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY . .

# Guard: the sample repos must arrive complete in the build context.
# A bare `data/` pattern in .gcloudignore previously stripped
# src/sample_repo/mlxtend/mlxtend/data, so every mlxtend data target
# (e.g. make_multiplexer_dataset) was absent from coverage reports.
RUN python -c "import pathlib; p = pathlib.Path('src/sample_repo/mlxtend/mlxtend'); assert p.is_dir() and (p / 'data').is_dir(), 'mlxtend data subpackage missing from build context; check .gcloudignore'"

# Copy evaluation inputs (dataset + prompt) into the image
COPY cloud/inputs /app/inputs

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
