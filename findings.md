# Findings & Context

## Current Architecture
- **Backend**: FastAPI (Python 3.14 - Note: Docker images for 3.14 might be experimental, stick to 3.11/3.12 for stability).
- **Frontend**: Svelte 5 + Vite.
- **Communication**: REST API + WebSocket (`ws://localhost:8000/ws`).
- **Data**: 
    - `backend/data/detected_errors.json` (Source of Truth)
    - `backend/data/stats.db` (SQLite Cache)

## Deployment Constraints (Free Tier)
- **Ephemeral Filesystem**: Most free PaaS (Render, Heroku) wipe the disk on restart.
    - *Impact*: `stats.db` will be deleted.
    - *Resolution*: The `DataStorage` class already has logic to rebuild SQLite from JSON. This is acceptable for a demo. The `detected_errors.json` must be included in the Docker image.
- **Port Binding**: Must use `$PORT` env var, not hardcoded 8000.
- **CORS**: Must allow the Vercel/Production domain.

## Codebase Audit
- **Frontend URLs**:
    - Need to check `App.svelte` or `store.js` or API services for hardcoded `localhost`.
- **Backend Host**:
    - `uvicorn` usually defaults to `127.0.0.1`. Must bind to `0.0.0.0`.
