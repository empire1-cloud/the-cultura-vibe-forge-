# AGENTS.md

## Cursor Cloud specific instructions

### Architecture Overview

Cultura Vibe OS is a full-stack AI code builder with a React 19 frontend (CRA + CRACO + Tailwind) and a Python FastAPI backend. MongoDB stores users, artifacts, billing, and rate events.

### Services

| Service | Port | Command |
|---------|------|---------|
| Backend (FastAPI) | 8080 | `cd backend && source venv/bin/activate && uvicorn server:app --host 0.0.0.0 --port 8080 --reload` |
| Frontend (React) | 3000 | `cd frontend && REACT_APP_BACKEND_URL=http://localhost:8080 yarn start` |
| MongoDB | 27017 | `sudo mongod --dbpath /data/db --fork --logpath /var/log/mongodb.log` |

### Required Environment Variables (backend)

- `MONGO_URL=mongodb://localhost:27017`
- `DB_NAME=cultura-vibe`
- `JWT_SECRET=<any-secret-string>`
- `EMERGENT_LLM_KEY=<anthropic-api-key>` (needed for LLM code generation; API endpoints respond 503 without it but auth/categories/billing work)

### Node Version

The frontend requires Node 20.x. Use `nvm use 20` before running frontend commands. Yarn 1.22 is the package manager (lockfile: `frontend/yarn.lock`).

### Python Version

The backend requires Python 3.11. A virtualenv at `backend/venv` is created with `python3.11 -m venv venv`.

### Lint

- **Backend:** `cd backend && source venv/bin/activate && flake8 server.py executor.py --max-line-length=120`
- **Frontend:** ESLint runs inline during `yarn start` and `yarn build` via CRACO. There is no standalone ESLint config file; rules are defined in `craco.config.js`.

### Tests

- **Backend:** `cd backend && source venv/bin/activate && REACT_APP_BACKEND_URL=http://localhost:8080 pytest tests/ -v`
  - Tests that call the LLM (`test_generate_artifact_structure`, `test_list_artifacts`, etc.) require a valid `EMERGENT_LLM_KEY` secret and a running backend.
  - Tests hit the live backend at `REACT_APP_BACKEND_URL`, not a test client.
- **Frontend:** `cd frontend && yarn test` (Jest + React Testing Library via CRA)

### Gotchas

- MongoDB must be started manually (`sudo mongod --dbpath /data/db --fork --logpath /var/log/mongodb.log`) since there is no systemd in the cloud VM.
- The backend test file `test_root` expects `"El Arquitecto AI"` but `server.py` returns `"Cultura Vibe"` — this is a pre-existing mismatch.
- The `craco.config.js` tries to load `@emergentbase/visual-edits/craco` in dev mode; this is optional and warns gracefully if missing.
- Frontend build output goes to `frontend/build/` — do not commit it.
