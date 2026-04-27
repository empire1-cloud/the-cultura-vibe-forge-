"""El Arquitecto AI — Cultural Engine Backend.

Soulfire Guardrails + Claude Sonnet 4.5 code boilerplate generator with SSE streaming forge.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ---------- Config ----------
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = 7

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("arquitecto")

app = FastAPI(title="El Arquitecto AI")
api = APIRouter(prefix="/api")


# ---------- Soulfire Guardrails ----------
CATEGORY_GUARDRAILS = {
    "music": (
        "Prioritize 48kHz / 24-bit lossless audio handling. Embed 'Emotional Math' — "
        "emotion-tagged waveform metadata. Every generated track/file MUST carry a "
        "Creator Equity DNA tag (ISO-like creator fingerprint, royalty-split scaffold)."
    ),
    "art_visual": (
        "Treat every pixel with reverence. Color-managed pipelines (Display-P3 or sRGB with ICC). "
        "Watermark + provenance metadata on export. Creator-owned licensing baked into the gallery model."
    ),
    "commerce": (
        "Build with Creator Equity first: transparent revenue splits, non-extractive payment flows, "
        "and a visible artist-share on every SKU. PCI-safe payment stubs. Clean, opinionated checkout."
    ),
    "community": (
        "Community-first moderation primitives. Consent-based content sharing. "
        "Zero-shadow-ban transparency log. Local-language support scaffolding and anti-surveillance defaults."
    ),
    "storytelling": (
        "Narrative-first data models (acts, beats, POV). First-person voice preserved. "
        "Exportable oral-history format with attribution + cultural context fields."
    ),
}

BASE_PREAMBLE = (
    "Act as a Chicano AI Architect — authoritative, craft-focused, minimalist. "
    "Build this project with high fidelity, cultural authenticity, and creator-owned equity. "
    "Ship production-grade code only. No placeholder TODOs. Follow the Soulfire Guardrails."
)


def cultural_refinement(user_prompt: str, category: str) -> str:
    """Prepend Soulfire Guardrails to the user's raw prompt."""
    guardrails = CATEGORY_GUARDRAILS.get(category, "")
    pieces = [BASE_PREAMBLE]
    if guardrails:
        pieces.append(f"Soulfire Guardrails ({category}): {guardrails}")
    pieces.append(f"User Vision: {user_prompt.strip()}")
    return "\n\n".join(pieces)


# ---------- Models ----------
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=60)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    display_name: str


class AuthOut(BaseModel):
    token: str
    user: UserOut


class GenerateIn(BaseModel):
    prompt: str = Field(min_length=8, max_length=4000)
    category: str = Field(pattern="^(music|art_visual|commerce|community|storytelling)$")
    title: Optional[str] = Field(default=None, max_length=80)


class CodeFile(BaseModel):
    path: str
    content: str


class Artifact(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    category: str
    prompt: str
    refined_prompt: str
    files: List[CodeFile]
    terminal_log: List[str]
    created_at: str


class ArtifactSummary(BaseModel):
    id: str
    title: str
    description: str
    category: str
    file_count: int
    created_at: str


# ---------- Auth helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------- Routes: Auth ----------
@api.get("/")
async def root():
    return {"service": "El Arquitecto AI", "status": "forjando"}


@api.post("/auth/signup", response_model=AuthOut)
async def signup(payload: SignupIn):
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": payload.email.lower(),
        "display_name": payload.display_name.strip(),
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = make_token(user_id)
    return AuthOut(
        token=token,
        user=UserOut(id=user_id, email=doc["email"], display_name=doc["display_name"]),
    )


@api.post("/auth/login", response_model=AuthOut)
async def login(payload: LoginIn):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = make_token(user["id"])
    return AuthOut(
        token=token,
        user=UserOut(id=user["id"], email=user["email"], display_name=user["display_name"]),
    )


@api.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(current_user)):
    return UserOut(id=user["id"], email=user["email"], display_name=user["display_name"])


# ---------- Routes: Generate ----------
SYSTEM_PROMPT = (
    "You are El Arquitecto — a Chicano AI Architect. You forge production-grade code boilerplates "
    "with cultural authenticity and creator-owned equity. You ALWAYS respond with STRICT JSON matching "
    "this exact schema and nothing else — no prose, no markdown fences:\n"
    "{\n"
    '  "title": "short project title (<=60 chars)",\n'
    '  "description": "1-2 sentence description of what was forged",\n'
    '  "files": [ { "path": "relative/path.ext", "content": "full file content" } ]\n'
    "}\n"
    "Generate between 3 and 8 files. Include a README.md that calls out the Soulfire Guardrails applied. "
    "Use modern, minimal, idiomatic code. No placeholders."
)


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in LLM response")
    return json.loads(text[start : end + 1])


def _normalize_files(raw_files) -> List[CodeFile]:
    files: List[CodeFile] = []
    for f in raw_files or []:
        if not isinstance(f, dict):
            continue
        path = str(f.get("path", "")).strip().lstrip("/")
        content = str(f.get("content", ""))
        if path and content:
            files.append(CodeFile(path=path, content=content))
    return files


TERMINAL_SCRIPT = [
    "> arquitecto init --soulfire",
    "[planning-agent] Architecting the Soulfire blueprint...",
    "[planning-agent] Setting the foundation...",
    "[cultural-filter] Injecting Soulfire Guardrails for category={category}",
    "[frontend-agent] Connecting the wires (geometric sans, chrome, candy apple red)...",
    "[backend-agent] Spinning up the Python server with {category} filters...",
    "[forge] Forging the Logic — calling Claude Sonnet 4.5...",
]


async def forge_logic_task(payload: GenerateIn) -> Tuple[dict, str]:
    """Run the LLM forge in a worker thread so the FastAPI loop stays responsive.

    `LlmChat.send_message` is `async def` but internally invokes a synchronous
    `litellm.completion`. Awaiting it blocks the event loop for the whole
    30-60s call. We isolate the call in a worker thread that owns its own
    event loop via `asyncio.run`, freeing the main loop to serve other requests.
    """
    refined = cultural_refinement(payload.prompt, payload.category)
    session_id = f"forge-{uuid.uuid4()}"

    def _run_blocking() -> str:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        return asyncio.run(chat.send_message(UserMessage(text=refined)))

    raw = await asyncio.to_thread(_run_blocking)
    data = _extract_json(raw)
    return data, refined


@api.post("/artifacts/generate", response_model=Artifact)
async def generate_artifact(payload: GenerateIn, user: dict = Depends(current_user)):
    """Non-streaming forge. Kept for programmatic use."""
    terminal_log: List[str] = [line.format(category=payload.category) for line in TERMINAL_SCRIPT]
    try:
        data, refined = await forge_logic_task(payload)
    except Exception as exc:
        logger.exception("LLM forge failed")
        raise HTTPException(status_code=502, detail=f"Forge failed: {exc}") from exc

    files = _normalize_files(data.get("files"))
    if not files:
        raise HTTPException(status_code=502, detail="Forge produced no files")

    title = (payload.title or data.get("title") or "Untitled Artifact").strip()[:80]
    description = (data.get("description") or "").strip()
    terminal_log.append(f"[forge] {len(files)} files forged.")
    terminal_log.append("[ok] Ready for the boulevard. Hecho con ganas.")

    artifact_id = str(uuid.uuid4())
    artifact = Artifact(
        id=artifact_id,
        user_id=user["id"],
        title=title,
        description=description,
        category=payload.category,
        prompt=payload.prompt,
        refined_prompt=refined,
        files=files,
        terminal_log=terminal_log,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await db.artifacts.insert_one(artifact.model_dump())
    return artifact


def _sse(event: str, **fields) -> str:
    return f"data: {json.dumps({'event': event, **fields})}\n\n"


@api.post("/artifacts/generate-stream")
async def generate_artifact_stream(payload: GenerateIn, user: dict = Depends(current_user)):
    """Real-time forge via Server-Sent Events.

    Emits `log` events as each agent stage completes, runs the LLM in a worker
    thread (event loop stays responsive), then emits a final `done` event with
    the persisted artifact id. Errors emit an `error` event.
    """

    async def event_gen():
        terminal_log: List[str] = []

        def push(msg: str) -> str:
            terminal_log.append(msg)
            return _sse("log", msg=msg)

        try:
            # Stage 1: prelude — staged so the user sees the agents come online.
            for raw_line in TERMINAL_SCRIPT:
                yield push(raw_line.format(category=payload.category))
                await asyncio.sleep(0.45)

            # Stage 2: actual forge (LLM in a worker thread).
            data, refined = await forge_logic_task(payload)

            files = _normalize_files(data.get("files"))
            if not files:
                yield _sse("error", msg="Forge produced no files")
                return

            title = (payload.title or data.get("title") or "Untitled Artifact").strip()[:80]
            description = (data.get("description") or "").strip()

            yield push(f"[forge] {len(files)} files forged.")
            yield push("[ok] Ready for the boulevard. Hecho con ganas.")

            artifact_id = str(uuid.uuid4())
            artifact = Artifact(
                id=artifact_id,
                user_id=user["id"],
                title=title,
                description=description,
                category=payload.category,
                prompt=payload.prompt,
                refined_prompt=refined,
                files=files,
                terminal_log=terminal_log,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            await db.artifacts.insert_one(artifact.model_dump())

            yield _sse("done", id=artifact_id, file_count=len(files), title=title)
        except Exception as exc:
            logger.exception("Forge stream failed")
            yield _sse("error", msg=str(exc))

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@api.get("/artifacts", response_model=List[ArtifactSummary])
async def list_artifacts(user: dict = Depends(current_user)):
    cursor = db.artifacts.find(
        {"user_id": user["id"]},
        {"_id": 0, "id": 1, "title": 1, "description": 1, "category": 1, "files": 1, "created_at": 1},
    ).sort("created_at", -1)
    out: List[ArtifactSummary] = []
    async for doc in cursor:
        out.append(
            ArtifactSummary(
                id=doc["id"],
                title=doc["title"],
                description=doc.get("description", ""),
                category=doc["category"],
                file_count=len(doc.get("files", [])),
                created_at=doc["created_at"],
            )
        )
    return out


@api.get("/artifacts/{artifact_id}", response_model=Artifact)
async def get_artifact(artifact_id: str, user: dict = Depends(current_user)):
    doc = await db.artifacts.find_one({"id": artifact_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return Artifact(**doc)


@api.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    request: Request,
    token: Optional[str] = Query(default=None),
):
    user_id: Optional[str] = None
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload["sub"]
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        u = await current_user(request)
        user_id = u["id"]

    doc = await db.artifacts.find_one({"id": artifact_id, "user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Artifact not found")

    buf = io.BytesIO()
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "-", doc["title"]).strip("-") or "artifact"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in doc.get("files", []):
            zf.writestr(f"{safe_title}/{f['path']}", f["content"])
        manifest = {
            "title": doc["title"],
            "category": doc["category"],
            "prompt": doc["prompt"],
            "refined_prompt": doc["refined_prompt"],
            "created_at": doc["created_at"],
        }
        zf.writestr(f"{safe_title}/SOULFIRE.json", json.dumps(manifest, indent=2))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.zip"'},
    )


@api.get("/categories")
async def categories():
    return [
        {"id": "music", "label": "Music", "tagline": "48kHz · Emotional Math · Creator Equity"},
        {"id": "art_visual", "label": "Art / Visual", "tagline": "Color-managed · Provenance · Owned"},
        {"id": "commerce", "label": "Commerce", "tagline": "Transparent splits · Non-extractive"},
        {"id": "community", "label": "Community", "tagline": "Consent-first · Zero shadow-ban"},
        {"id": "storytelling", "label": "Storytelling", "tagline": "First-person · Oral-history export"},
    ]


# ---------- Wiring ----------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
