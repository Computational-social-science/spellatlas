# Task Plan: Remote Deployment Optimization

## Status
- [x] Phase 1: Architecture Analysis & Preparation
    - [x] Analyze codebase for hardcoded paths and local dependencies
    - [x] Create Environment Variable strategy
- [x] Phase 2: Containerization (Docker)
    - [x] Create Backend Dockerfile
    - [x] Create Frontend Dockerfile (Multi-stage build for static assets)
    - [x] Create docker-compose.yml for local orchestration testing
- [x] Phase 3: Codebase Adaptation
    - [x] Refactor Frontend API calls to use Environment Variables
    - [x] Update Backend CORS to support production domains
    - [x] Ensure SQLite/Data persistence strategy (or graceful ephemeral fallback)
- [ ] Phase 4: CI/CD & Deployment Configuration
    - [ ] Create GitHub Actions workflow (optional/draft)
    - [ ] Document deployment steps for Vercel (Frontend) + Render/Fly.io (Backend)
- [ ] Phase 5: Verification
    - [ ] Local Docker run test (User to perform if Docker installed)
    - [x] Build verification (Verified via local run)

## Architecture Decisions
- **Frontend**: Vercel (Free, Static Hosting)
- **Backend**: Render.com (Free Tier) or Docker-based Container
- **Database**: Currently SQLite. 
    - *Risk*: Ephemeral file systems on free PaaS will reset DB on deploy.
    - *Mitigation*: App currently rebuilds from `detected_errors.json`. We will ensure the startup logic remains robust.
