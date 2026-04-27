# El Arquitecto AI — PRD

**Last updated:** Feb 2026 (initial MVP)

## Original Problem Statement
Build a "Vibe Coding" app builder — a culturally-tuned version of Emergent. Aesthetic: **Cyber-Chicano** (Dark mode + Chrome accents + Candy Apple Red #C8102E). Three core surfaces:
- **El Centro** — large glowing prompt input
- **El Terminal** — live AI-agent feedback window
- **The Taller** — gallery of Digital Artifacts (completed apps)

Backend has a **Cultural Filter** that prepends *Soulfire Guardrails* to every prompt before it hits the LLM (e.g. Music → 48kHz / Emotional Math / Creator Equity DNA tagging).

Language: English with professional Chicano English terminology only (no forced Spanglish). "Con Ganas" button, "Forging the Logic" status, "The Taller" gallery.

## User Choices (locked in)
- **LLM:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) via Emergent Universal LLM Key
- **Scope:** Full flow including downloadable `.zip` of generated boilerplate
- **Auth:** Email + password (JWT) — per-user gallery
- **Categories:** Music, Art/Visual, Commerce, Community, Storytelling
- **Typography:** Space Grotesk (display) · Manrope (body) · JetBrains Mono (terminal) — no Gothic

## Architecture
- **Frontend:** React 19 + React Router v7 + Tailwind + shadcn/ui, sonner toasts
- **Backend:** FastAPI + motor (MongoDB) + bcrypt + PyJWT + `emergentintegrations.llm.chat` (Claude)
- **Auth:** JWT in `Authorization: Bearer` header, stored client-side in `localStorage.arq_token`
- **Zip download:** supports `?token=` query param so direct browser links work

## Implemented (Feb 2026)
- Signup / login / me endpoints with bcrypt + JWT
- Cultural Filter (`cultural_refinement`) with 5 category-specific Soulfire Guardrails
- `POST /api/artifacts/generate` → Claude Sonnet 4.5 generates strict-JSON boilerplate (3–8 files) → persisted to MongoDB with full refined prompt + terminal log
- `GET /api/artifacts` (owner-scoped list) + `GET /api/artifacts/{id}` + `GET /api/artifacts/{id}/download` (streams zip with `SOULFIRE.json` manifest)
- Landing (hero + terminal teaser + value props), Login, Signup
- Dashboard: El Centro textarea, 5-category grid, Con Ganas button, live El Terminal with per-line streaming logs
- The Taller: grid of user artifacts, empty state
- Artifact detail: file tabs, code viewer, download zip, forge-log sidebar, refined-prompt accordion
- Testing agent integration validated core auth + CRUD; LLM generate blocked by exhausted Universal Key budget

## Known Issues / Next Steps
- **P0 — Universal Key budget exceeded** (`Current cost: 0.43 / Max budget: 0.4`). User must top up via Profile → Universal Key → Add Balance before generations will succeed.
- **P1 — Event-loop blocking on generate**: the sync `litellm.completion` under `emergentintegrations` blocks the FastAPI worker for the duration of the LLM call. Fix by wrapping in `asyncio.to_thread` or switching to `litellm.acompletion`.
- **P2 — Streaming log**: replace the client-side simulated terminal with true SSE/WebSocket updates from the backend once the generation is async.
- **P2 — Public sharing**: toggle per artifact to share a read-only link.
- **P2 — Preview/sandbox**: in-browser preview of a forged artifact (future).

## Test Accounts
See `/app/memory/test_credentials.md`. No pre-seeded users — testing agent creates on the fly.
