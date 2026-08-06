FROM python:3.11-slim

RUN pip install --no-cache-dir "coverup==0.6.3" "pytest>=8" "coverage>=7"
RUN useradd --create-home runner
USER runner
WORKDIR /workspace
