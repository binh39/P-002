# PromptOpt architecture index

Sơ đồ components, deployment boundaries và hai dataflow chính được duy trì tại [docs/architecture_diagram.md](docs/architecture_diagram.md).

Kiến trúc hiện tại gồm:

- React 19 + TypeScript + Vite frontend;
- FastAPI application backend;
- Firebase Authentication và Hosting;
- Firestore cho metadata/audit, GCS cho source và artifacts;
- Cloud Tasks gọi các internal API bằng OIDC;
- Cloud Run Job chạy CoverUp + DSPy/GEPA + pytest/SlipCover;
- Vertex AI Gemini cho test generation và prompt reflection.

Repository không sử dụng LangGraph, RAG/vector store, Next.js hay PostgreSQL trong production path. Khi code thay đổi, cập nhật sơ đồ canonical nói trên và kiểm tra lại các nguồn sau:

- `app/backend/services/container.py`
- `app/backend/modules/*/router.py`
- `app/backend/modules/experiments/service.py`
- `app/backend/modules/experiments/cloud_optimizer.py`
- `app/frontend/src/app/providers.tsx`
- `cloud/run_job.py`
