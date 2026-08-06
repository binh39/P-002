FROM python:3.11-slim

RUN pip install --no-cache-dir "coverup==0.6.3" "pytest>=8" "coverage>=7" "litellm[google]>=1.94.0"
RUN useradd --create-home runner
COPY runner_entry.py /opt/promptopt/runner_entry.py
USER runner
WORKDIR /workspace
