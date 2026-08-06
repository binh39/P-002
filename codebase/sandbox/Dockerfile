FROM python:3.11-slim

RUN pip install --no-cache-dir "coverup==0.6.3" "pytest>=8" "coverage>=7" "litellm[google]>=1.94.0" "google-cloud-storage>=2.19.0"
RUN useradd --create-home runner
COPY sandbox/runner_entry.py /opt/promptopt/runner_entry.py
COPY sandbox/cloud_job_entry.py /opt/promptopt/cloud_job_entry.py
COPY src/modules/experiments/traces.py /opt/promptopt/traces.py
USER runner
WORKDIR /workspace

CMD ["python", "/opt/promptopt/cloud_job_entry.py"]
