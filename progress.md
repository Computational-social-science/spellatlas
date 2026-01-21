# Progress Log

## 2026-01-21
- **Optimization for Remote Deployment**
    - Created `Dockerfile.backend` (Python 3.11-slim) and `Dockerfile.frontend` (Node 18 -> Nginx).
    - Created `docker-compose.yml` for orchestration.
    - Refactored Frontend to use environment variables (`VITE_API_URL`, `VITE_WS_URL`) via `.env`.
    - Updated Backend CORS to support `ALLOWED_ORIGINS` environment variable.
    - Verified local execution with updated configuration.
