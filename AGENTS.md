# AGENTS.md

## Cursor Cloud specific instructions

### Architecture Overview
Two-service monorepo: FastAPI backend (Python 3.11) + React 19 frontend (CRA + CRACO, Node 20, yarn).

### Services

| Service | Port | Start Command |
|---------|------|---------------|
| Backend (FastAPI) | 8080 | `source backend/.venv/bin/activate && cd backend && uvicorn server:app --host 0.0.0.0 --port 8080 --reload` |
| Frontend (React) | 3000 | `cd frontend && REACT_APP_BACKEND_URL=http://localhost:8080 BROWSER=none yarn start` |
| MongoDB | 27017 | `mongod --dbpath /data/db --bind_ip 127.0.0.1 --port 27017` |

### Required Environment Variables (backend)
Set these before starting the backend (the startup guard returns 503 on ALL non-diagnostic routes if any are missing):
- `MONGO_URL` — e.g. `mongodb://127.0.0.1:27017`
- `DB_NAME` — e.g. `cultura-vibe`
- `JWT_SECRET` — any string for dev (e.g. `dev-secret-key-for-testing`)
- `EMERGENT_LLM_KEY` — Anthropic API key (required even as placeholder to pass startup guard; actual key needed for LLM generation)

### Running Tests
```bash
# Backend (against running server on port 8080):
source backend/.venv/bin/activate
REACT_APP_BACKEND_URL="http://localhost:8080" pytest backend/tests/ -v

# Frontend build (includes ESLint checks via CRACO):
cd frontend && REACT_APP_BACKEND_URL=http://localhost:8080 yarn build
```

### Lint
```bash
# Backend:
source backend/.venv/bin/activate && flake8 backend/server.py backend/executor.py --max-line-length=120

# Frontend: ESLint runs integrated via CRACO during `yarn start` and `yarn build`.
# There is no standalone eslint.config.js — ESLint 9 flat config is NOT used; 
# CRA's built-in ESLint config is extended through craco.config.js.
```

### Key Gotchas
- **Node version**: Must use Node 20 (`nvm use 20`). The frontend `package.json` specifies `"engines": {"node": "20.x"}`.
- **Python version**: Backend requires Python 3.11. A venv at `backend/.venv` is used.
- **Startup guard**: The backend middleware at `runtime_config_guard` checks env vars at import time. Changing env vars requires a server restart (the `--reload` flag doesn't pick up env var changes since the check is done at module level).
- **Frontend ESLint**: Do NOT run `npx eslint` standalone — it expects ESLint 9 flat config which doesn't exist. Linting is integrated into `yarn start`/`yarn build` via CRACO.
- **Test service name mismatch**: The test file `test_arquitecto.py` expects `"El Arquitecto AI"` for the service name but the code returns `"Cultura Vibe"`. This is a pre-existing mismatch in the repo.
- **LLM tests**: Tests that depend on `generated_artifact` fixture require a valid Anthropic API key in `EMERGENT_LLM_KEY` to pass.
- **MongoDB**: Must be running before backend starts. Data directory is `/data/db`.
