"""Cultura Vibe OS — Cultural Engine Backend.

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

import httpx  # direct Anthropic calls — no emergentintegrations needed

from executor import run_artifact as _exec_run_artifact, detect_plan as _exec_detect_plan

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

app = FastAPI(title="Cultura Vibe OS")
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
    "Act as the Cultura Vibe Engine. You are an elite, craft-focused AI Architect. "
    "Every line of code must reflect high-fidelity Chicano engineering standards: "
    "Precision, Soul, and Creator Equity. Ship production-grade code only — no placeholder TODOs. "
    "Follow the Soulfire Guardrails."
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
    return {"service": "Cultura Vibe", "status": "active", "mode": "con_ganas"}


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
        "tier": "aprendiz",
        "tier_until": None,
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
    "You are the Cultura Vibe Engine — an elite Chicano AI Architect. You forge production-grade "
    "code boilerplates with cultural authenticity and creator-owned equity. You ALWAYS respond "
    "with STRICT JSON matching this exact schema and nothing else — no prose, no markdown fences:\n"
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

    async def _call_claude(prompt_text: str, sys_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": EMERGENT_LLM_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-4-5-20250929", "max_tokens": 4096, "system": sys_prompt, "messages": [{"role": "user", "content": prompt_text}]},
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]

    raw = await _call_claude(refined, SYSTEM_PROMPT)
    data = _extract_json(raw)
    return data, refined


@api.post("/artifacts/generate", response_model=Artifact)
async def generate_artifact(payload: GenerateIn, user: dict = Depends(current_user)):
    """Non-streaming forge. Kept for programmatic use."""
    await _rate_acquire(user)
    try:
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
    finally:
        await _rate_release(user["id"])


def _sse(event: str, **fields) -> str:
    return f"data: {json.dumps({'event': event, **fields})}\n\n"


# ---------- Rate limit (Mongo-backed, tier-aware) ----------
RATE_HOUR_SECONDS = 3600
RATE_DAY_SECONDS = 86400

TIER_LIMITS = {
    "aprendiz": {"hour": 5, "day": 10, "concurrent": 1, "included_monthly": 0},
    "soulfire": {"hour": 20, "day": 100, "concurrent": 2, "included_monthly": 25, "overage_price": 2.00},
    "maestro": {"hour": 60, "day": 300, "concurrent": 3, "included_monthly": 100, "overage_price": 1.00},
    # Legacy aliases for backward compat
    "maestro_elite": {"hour": 20, "day": 100, "concurrent": 2, "included_monthly": 25, "overage_price": 2.00},
    "maestro_master": {"hour": 60, "day": 300, "concurrent": 3, "included_monthly": 100, "overage_price": 1.00},
}

_rate_active: dict[str, int] = {}  # in-flight only — fine to keep in-memory
_rate_lock = asyncio.Lock()
_rate_index_ready = False


async def _ensure_rate_index() -> None:
    global _rate_index_ready
    if _rate_index_ready:
        return
    # TTL index: documents auto-expire 24h+ after creation.
    await db.rate_events.create_index("ts", expireAfterSeconds=RATE_DAY_SECONDS + 60)
    await db.rate_events.create_index([("user_id", 1), ("ts", -1)])
    _rate_index_ready = True


def _user_tier(user: dict) -> str:
    """Return the active tier — falls back to aprendiz if pass expired."""
    tier = user.get("tier") or "aprendiz"
    until = user.get("tier_until")
    if tier == "maestro" and until:
        try:
            if datetime.fromisoformat(until) < datetime.now(timezone.utc):
                return "aprendiz"
        except ValueError:
            return "aprendiz"
    return tier


async def _rate_acquire(user: dict) -> None:
    """Reserve a forge slot or raise 429. Persists usage history in Mongo.

    Paid tiers (Elite/Master) have an `included_monthly` quota. Once exhausted,
    the user must have `forge_credits > 0` — we burn one credit per overage forge.
    Without credits, we 429 with a credit-pack CTA.
    """
    await _ensure_rate_index()
    user_id = user["id"]
    tier = _user_tier(user)
    limits = TIER_LIMITS[tier]
    now = datetime.now(timezone.utc)
    hour_cutoff = now - timedelta(seconds=RATE_HOUR_SECONDS)
    day_cutoff = now - timedelta(seconds=RATE_DAY_SECONDS)

    async with _rate_lock:
        hour_count = await db.rate_events.count_documents(
            {"user_id": user_id, "ts": {"$gte": hour_cutoff}}
        )
        if hour_count >= limits["hour"]:
            oldest = await db.rate_events.find_one(
                {"user_id": user_id, "ts": {"$gte": hour_cutoff}},
                sort=[("ts", 1)],
            )
            retry_in = RATE_HOUR_SECONDS
            if oldest and "ts" in oldest:
                retry_in = max(int(RATE_HOUR_SECONDS - (now - oldest["ts"]).total_seconds()), 1)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Hourly forge limit reached ({limits['hour']}/hr on {tier}). "
                    f"Retry in {retry_in}s — or upgrade."
                ),
                headers={"Retry-After": str(retry_in), "X-Tier": tier, "X-Upgrade": "/billing"},
            )

        day_count = await db.rate_events.count_documents(
            {"user_id": user_id, "ts": {"$gte": day_cutoff}}
        )
        if day_count >= limits["day"]:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily forge limit reached ({limits['day']}/day on {tier}). "
                    "Upgrade to keep forging."
                ),
                headers={"X-Tier": tier, "X-Upgrade": "/billing"},
            )

        if _rate_active.get(user_id, 0) >= limits["concurrent"]:
            raise HTTPException(
                status_code=429,
                detail=f"Too many forges in flight (max {limits['concurrent']} on {tier}).",
                headers={"X-Tier": tier},
            )

        # Monthly included-quota check (paid tiers only).
        included = limits.get("included_monthly", 0) or 0
        cycle_started = (user or {}).get("cycle_started_at")
        cycle_used = 0
        used_credit = False
        if included > 0 and cycle_started:
            try:
                cycle_dt = datetime.fromisoformat(cycle_started)
                cycle_used = await db.rate_events.count_documents(
                    {"user_id": user_id, "ts": {"$gte": cycle_dt}, "billable": True}
                )
            except ValueError:
                cycle_used = 0

            if cycle_used >= included:
                # Overage: try to burn a credit atomically.
                upd = await db.users.find_one_and_update(
                    {"id": user_id, "forge_credits": {"$gt": 0}},
                    {"$inc": {"forge_credits": -1}},
                    return_document=True,
                )
                if not upd:
                    overage_price = limits.get("overage_price")
                    raise HTTPException(
                        status_code=402,
                        detail=(
                            f"Included {included} forges used this cycle. "
                            f"Buy a credit ({'$' + format(overage_price, '.2f') if overage_price else 'overage rate'}) to continue."
                        ),
                        headers={"X-Tier": tier, "X-Upgrade": "/billing", "X-Need-Credit": "1"},
                    )
                used_credit = True

        await db.rate_events.insert_one(
            {
                "user_id": user_id,
                "ts": now,
                "tier": tier,
                "billable": True,
                "billed_via": "credit" if used_credit else "included",
            }
        )
        _rate_active[user_id] = _rate_active.get(user_id, 0) + 1


async def _rate_release(user_id: str) -> None:
    async with _rate_lock:
        if _rate_active.get(user_id, 0) > 0:
            _rate_active[user_id] -= 1


@api.post("/artifacts/generate-stream")
async def generate_artifact_stream(payload: GenerateIn, user: dict = Depends(current_user)):
    """Real-time forge via Server-Sent Events.

    - `log` events for each agent stage (live)
    - `: ping` heartbeats every 15s during the long LLM call (proxy keep-alive)
    - `file` events as each generated file is finalized
    - final `done` event with artifact id, or `error`
    """
    await _rate_acquire(user)

    queue: asyncio.Queue = asyncio.Queue()
    SENTINEL = object()

    # Compute usage post-acquire to surface a discreet [forge-meter] cue if at 80%+.
    usage_counts = await _usage_counts(user["id"])
    tier = _user_tier(user)
    hour_limit = TIER_LIMITS[tier]["hour"]
    hour_used = usage_counts["hour_used"]
    show_meter = hour_used >= int(0.8 * hour_limit)

    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(15)
                await queue.put(": ping\n\n")
        except asyncio.CancelledError:
            return

    async def forge():
        terminal_log: List[str] = []

        async def push_log(msg: str):
            terminal_log.append(msg)
            await queue.put(_sse("log", msg=msg))

        try:
            for raw_line in TERMINAL_SCRIPT:
                await push_log(raw_line.format(category=payload.category))
                await asyncio.sleep(0.45)

            if show_meter:
                await push_log(
                    f"[forge-meter] {hour_used} / {hour_limit} used (Hustle accordingly.)"
                )

            data, refined = await forge_logic_task(payload)

            files = _normalize_files(data.get("files"))
            if not files:
                await queue.put(_sse("error", msg="Forge produced no files"))
                return

            title = (payload.title or data.get("title") or "Untitled Artifact").strip()[:80]
            description = (data.get("description") or "").strip()

            # Per-file events — emit each file as it lands so the UI can show progress.
            for f in files:
                line_count = f.content.count("\n") + 1
                await queue.put(
                    _sse("file", path=f.path, lines=line_count, bytes=len(f.content))
                )
                terminal_log.append(f"[file] {f.path} ({line_count} lines)")
                await queue.put(_sse("log", msg=f"[file] {f.path} ({line_count} lines)"))
                await asyncio.sleep(0.05)

            await push_log(f"[forge] {len(files)} files forged.")
            await push_log("[ok] Ready for the boulevard. Hecho con ganas.")

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

            await queue.put(
                _sse("done", id=artifact_id, file_count=len(files), title=title)
            )
        except Exception as exc:
            logger.exception("Forge stream failed")
            await queue.put(_sse("error", msg=str(exc)))

    async def event_gen():
        forge_task = asyncio.create_task(forge())
        heartbeat_task = asyncio.create_task(heartbeat())

        async def signal_done(_):
            await queue.put(SENTINEL)

        forge_task.add_done_callback(lambda t: asyncio.create_task(signal_done(t)))

        try:
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break
                yield item
            # Drain any remaining items pushed after sentinel was queued (rare).
            while not queue.empty():
                item = queue.get_nowait()
                if item is not SENTINEL:
                    yield item
        finally:
            heartbeat_task.cancel()
            if not forge_task.done():
                forge_task.cancel()
            await _rate_release(user["id"])

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


# ---------- Billing (Stripe Checkout) ----------
# Accept either name — playbook uses STRIPE_API_KEY, Stripe docs commonly say STRIPE_SECRET_KEY.
STRIPE_API_KEY = (os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY", "")).strip()
LIVE_MODE = STRIPE_API_KEY.startswith("sk_live_")

# Backend-defined packages — frontend never sets the price.
BILLING_PACKAGES = {
    "soulfire": {
        "amount": 29.00,
        "currency": "usd",
        "label": "Soulfire",
        "tagline": "$29/mo · 25 executions included · $2 per overage execution",
        "tier": "soulfire",
        "duration_days": 30,
        "mode": "subscription",
        "interval": "month",
        "lookup_key": "cultura_soulfire_v1",
        "product_name": "Cultura Vibe — Soulfire",
    },
    "maestro": {
        "amount": 149.00,
        "currency": "usd",
        "label": "Maestro",
        "tagline": "$149/mo · 100 executions included · $1 per overage · demo reel",
        "tier": "maestro",
        "duration_days": 30,
        "mode": "subscription",
        "interval": "month",
        "lookup_key": "cultura_maestro_v1",
        "product_name": "Cultura Vibe — Maestro",
    },
    "credits_soulfire_5": {
        "amount": 10.00,
        "currency": "usd",
        "label": "+5 Execution Credits · Soulfire",
        "tagline": "5 extra executions at $2 each",
        "tier_required": "soulfire",
        "credits": 5,
        "duration_days": 0,
        "mode": "payment",
    },
    "credits_maestro_10": {
        "amount": 10.00,
        "currency": "usd",
        "label": "+10 Execution Credits · Maestro",
        "tagline": "10 extra executions at $1 each",
        "tier_required": "maestro",
        "credits": 10,
        "duration_days": 0,
        "mode": "payment",
    },
}


_subscription_price_cache: dict[str, str] = {}


def _ensure_recurring_price(pkg: dict) -> str:
    """Lookup-or-create a recurring Stripe Price. Returns price_id.

    Cached in memory after first lookup; idempotent via Stripe's lookup_keys.
    """
    import stripe as stripe_sdk

    lookup_key = pkg["lookup_key"]
    if lookup_key in _subscription_price_cache:
        return _subscription_price_cache[lookup_key]

    stripe_sdk.api_key = STRIPE_API_KEY
    found = stripe_sdk.Price.list(lookup_keys=[lookup_key], expand=["data.product"], limit=1)
    if found and found.data:
        price_id = found.data[0].id
        _subscription_price_cache[lookup_key] = price_id
        return price_id

    product = stripe_sdk.Product.create(name=pkg["product_name"])
    price = stripe_sdk.Price.create(
        unit_amount=int(round(pkg["amount"] * 100)),
        currency=pkg["currency"],
        recurring={"interval": pkg["interval"]},
        product=product.id,
        lookup_key=lookup_key,
    )
    _subscription_price_cache[lookup_key] = price.id
    return price.id


class CheckoutIn(BaseModel):
    package_id: str = Field(pattern="^[a-z_]+$")
    origin_url: str = Field(min_length=8, max_length=300)


def _stripe_client(http_request: Request = None):
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_API_KEY
        return _stripe
    except ImportError:
        raise HTTPException(503, "stripe package not installed")


@api.get("/billing/packages")
async def billing_packages():
    out = []
    for k, v in BILLING_PACKAGES.items():
        out.append(
            {
                "id": k,
                "amount": v["amount"],
                "currency": v["currency"],
                "label": v["label"],
                "tagline": v["tagline"],
                "duration_days": v["duration_days"],
                "mode": v.get("mode", "payment"),
                "interval": v.get("interval"),
                "tier": v.get("tier"),
                "tier_required": v.get("tier_required"),
                "credits": v.get("credits", 0),
            }
        )
    return {"packages": out, "live_mode": LIVE_MODE}


@api.get("/billing/me")
async def billing_me(user: dict = Depends(current_user)):
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    tier = _user_tier(fresh or user)
    return {
        "tier": tier,
        "tier_until": (fresh or user).get("tier_until"),
        "subscription_id": (fresh or user).get("stripe_subscription_id"),
        "limits": TIER_LIMITS[tier],
        "forge_credits": (fresh or user).get("forge_credits", 0),
        "live_mode": LIVE_MODE,
    }


async def _usage_counts(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    hour_cutoff = now - timedelta(seconds=RATE_HOUR_SECONDS)
    day_cutoff = now - timedelta(seconds=RATE_DAY_SECONDS)
    hour_used = await db.rate_events.count_documents({"user_id": user_id, "ts": {"$gte": hour_cutoff}})
    day_used = await db.rate_events.count_documents({"user_id": user_id, "ts": {"$gte": day_cutoff}})
    return {"hour_used": hour_used, "day_used": day_used}


@api.get("/billing/usage")
async def billing_usage(user: dict = Depends(current_user)):
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    tier = _user_tier(fresh or user)
    limits = TIER_LIMITS[tier]
    counts = await _usage_counts(user["id"])
    concurrent = _rate_active.get(user["id"], 0)
    pct_hour = round(100 * counts["hour_used"] / max(limits["hour"], 1))

    # Cycle-included usage (for paid tiers).
    included = limits.get("included_monthly", 0)
    cycle_used = 0
    if included > 0 and (fresh or user).get("cycle_started_at"):
        try:
            cycle_dt = datetime.fromisoformat((fresh or user)["cycle_started_at"])
            cycle_used = await db.rate_events.count_documents(
                {"user_id": user["id"], "ts": {"$gte": cycle_dt}, "billable": True}
            )
        except ValueError:
            cycle_used = 0

    return {
        "tier": tier,
        "hour": {"used": counts["hour_used"], "limit": limits["hour"], "pct": pct_hour},
        "day": {"used": counts["day_used"], "limit": limits["day"]},
        "concurrent": {"used": concurrent, "limit": limits["concurrent"]},
        "cycle": {"used": cycle_used, "included": included},
        "forge_credits": (fresh or user).get("forge_credits", 0),
        "warn": pct_hour >= 80 or (included > 0 and cycle_used >= included),
        "live_mode": LIVE_MODE,
    }


@api.post("/billing/checkout")
async def billing_checkout(payload: CheckoutIn, http_request: Request, user: dict = Depends(current_user)):
    import stripe as _stripe
    _stripe.api_key = STRIPE_API_KEY

    pkg = BILLING_PACKAGES.get(payload.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Unknown package")

    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/billing?canceled=1"

    metadata = {
        "user_id": str(user["id"]),
        "user_email": user.get("email", ""),
        "package_id": payload.package_id,
        "tier": pkg.get("tier") or pkg.get("tier_required") or "credits",
        "mode": pkg.get("mode", "payment"),
        "credits": str(pkg.get("credits", 0)),
    }

    line_item = {
        "price_data": {
            "currency": pkg.get("currency", "usd"),
            "unit_amount": int(float(pkg["amount"]) * 100),
            "product_data": {"name": pkg.get("label", payload.package_id)},
            **({"recurring": {"interval": "month"}} if pkg.get("mode") == "subscription" else {}),
        },
        "quantity": 1,
    }

    session_params = {
        "mode": "subscription" if pkg.get("mode") == "subscription" else "payment",
        "line_items": [line_item],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata,
    }
    if user.get("email"):
        session_params["customer_email"] = user["email"]

    session = await asyncio.to_thread(_stripe.checkout.Session.create, **session_params)
    chosen_mode = session_params["mode"]

    await db.payment_transactions.insert_one(
        {
            "session_id": session.session_id,
            "user_id": user["id"],
            "user_email": user["email"],
            "package_id": payload.package_id,
            "amount": pkg["amount"],
            "currency": pkg["currency"],
            "tier": pkg.get("tier"),
            "duration_days": pkg["duration_days"],
            "mode": pkg.get("mode", "payment"),
            "credits": pkg.get("credits", 0),
            "status": "initiated",
            "payment_status": "unpaid",
            "applied": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return {"session_id": session.session_id, "url": session.url, "mode": chosen_mode}


async def _apply_paid_session(session_id: str) -> dict:
    """Idempotently grant tier upgrade OR credit top-up when Stripe confirms payment."""
    tx = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "applied": {"$ne": True}, "payment_status": "paid"},
        {"$set": {"applied": True, "applied_at": datetime.now(timezone.utc).isoformat()}},
        return_document=True,
    )
    if not tx:
        return {"granted": False}

    # Credit-pack purchase: just bump the user's credit balance.
    credits = tx.get("credits") or 0
    if credits:
        await db.users.update_one(
            {"id": tx["user_id"]},
            {"$inc": {"forge_credits": int(credits)}},
        )
        return {"granted": True, "credits_added": int(credits)}

    # Tier upgrade (Elite/Master): set tier + expiry.
    until = datetime.now(timezone.utc) + timedelta(days=int(tx.get("duration_days", 30)))
    await db.users.update_one(
        {"id": tx["user_id"]},
        {
            "$set": {
                "tier": tx.get("tier", "maestro_elite"),
                "tier_until": until.isoformat(),
                "cycle_started_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    return {"granted": True, "tier": tx.get("tier"), "tier_until": until.isoformat()}


@api.get("/billing/checkout/status/{session_id}")
async def billing_checkout_status(
    session_id: str, http_request: Request, user: dict = Depends(current_user)
):
    tx = await db.payment_transactions.find_one(
        {"session_id": session_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    sc = _stripe_client(http_request)
    stripe_status = await sc.get_checkout_status(session_id)

    payment_status = stripe_status.payment_status
    sess_status = stripe_status.status

    update = {"status": sess_status, "payment_status": payment_status}
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

    granted = None
    if payment_status == "paid":
        granted = await _apply_paid_session(session_id)

    return {
        "session_id": session_id,
        "status": sess_status,
        "payment_status": payment_status,
        "amount": tx["amount"],
        "currency": tx["currency"],
        "applied": bool(granted and granted.get("granted")) or tx.get("applied", False),
        "tier": (granted or {}).get("tier"),
        "tier_until": (granted or {}).get("tier_until"),
    }


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    sc = _stripe_client(request)
    try:
        event = await sc.handle_webhook(body, sig)
    except Exception as exc:
        logger.exception("Stripe webhook verification failed")
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    if event.payment_status == "paid" and event.session_id:
        await db.payment_transactions.update_one(
            {"session_id": event.session_id},
            {"$set": {"payment_status": "paid", "status": "complete"}},
        )
        await _apply_paid_session(event.session_id)
    return {"received": True, "event_type": event.event_type}


# ---------- Orchestrator (Amplifier Drafts) ----------
PLATFORMS = {
    "x": {
        "label": "X",
        "char_limit": 280,
        "voice": "Technical authority, terse, no hashtags-as-decoration. End with a single power line.",
    },
    "instagram": {
        "label": "Instagram",
        "char_limit": 2200,
        "voice": "Visual-first caption. Short hook, then one paragraph of craft narrative. 4-6 hashtags, single line, all lowercase.",
    },
    "tiktok": {
        "label": "TikTok",
        "char_limit": 300,
        "voice": "Punchy hook, vocal-archetype mention, music tag. 2-3 hashtags max.",
    },
    "linkedin": {
        "label": "LinkedIn",
        "char_limit": 1500,
        "voice": "B2B case-study tone. Lead with the engineering insight, end with the equity model. No hashtags except 1-2 industry tags.",
    },
}

UNIVERSES = {
    "cultura": {
        "label": "CULTURA Vibe",
        "aesthetic": (
            "Sleek, minimalist. Brushed chrome surfaces, candy apple red (#C8102E) accents only. "
            "Geometric sans-serif typography (Space Grotesk). Dark canvas. No carousels."
        ),
        "narrative": "Pride · Equity · Engineering Craftsmanship",
    },
    "nothing": {
        "label": "Nothing Protocol",
        "aesthetic": (
            "Dot-matrix typography. Transparent, layered surfaces. Stark white-on-black. "
            "Candy apple red ONLY on the existing red LED indicator points — accent, not takeover. "
            "Essentialism. Negative space generously used."
        ),
        "narrative": "Minimalism · Engineering · Essentialism · Soulfire meets Nothing",
    },
}


class DraftGenerateIn(BaseModel):
    artifact_id: str
    platforms: List[str] = Field(min_length=1, max_length=4)
    universe: str = Field(default="cultura", pattern="^(cultura|nothing)$")


def soulfire_filter(payload: dict) -> Tuple[bool, List[str]]:
    """Run a draft through the Soulfire content filter.

    Returns (passed, reasons) — reasons populated on rejection or warnings.
    """
    flags: List[str] = []
    text = (payload.get("caption") or "").lower()

    forbidden = ["yo homies", "esé", "ese ", "vato", "carnal", "homie", "loco mode"]
    for phrase in forbidden:
        if phrase in text:
            flags.append(f"cliche:{phrase.strip()}")

    cultural_signals = ["pride", "equity", "engineering", "craftsmanship", "creator", "soulfire"]
    if not any(sig in text for sig in cultural_signals):
        flags.append("cultural:no_authentic_signal")

    if (payload.get("audio_brief") or "") and "48khz" not in text and "48khz" not in (payload.get("audio_brief") or "").lower():
        flags.append("technical:audio_missing_48khz")

    if "creator equity" not in text and "dna" not in text and (payload.get("audio_brief") or ""):
        flags.append("technical:audio_missing_dna_tag")

    rejecting = [f for f in flags if f.startswith("cliche:")]
    return (len(rejecting) == 0, flags)


DRAFT_SYSTEM_PROMPT = (
    "You are the Cultura Vibe Amplifier — Chief Distribution Officer for the Cultura Vibe ecosystem. "
    "Tone: professional Chicano English. Authoritative, minimalist, craft-focused. NO clichés, NO forced "
    "Spanglish (no 'vato', 'esé', 'homie', 'loco'). Cultural pride is felt through engineering excellence "
    "and creator equity, not language caricature. "
    "Respond with STRICT JSON only — no prose, no fences:\n"
    "{\n"
    '  "drafts": [\n'
    '    { "platform": "<platform_id>", "caption": "<full post copy>", "hashtags": ["#tag1", "#tag2"],\n'
    '      "mockup_brief": "<one-paragraph art-direction brief for the visual asset>",\n'
    '      "audio_brief": "<empty string OR audio snippet brief — mandatory mention of 48kHz + Creator Equity DNA>",\n'
    '      "alt_text": "<accessibility alt text for the mockup>" }\n'
    "  ]\n"
    "}\n"
    "Every caption must mention pride, equity, or engineering craftsmanship — at least one. "
    "Audio briefs (when present) MUST cite 48kHz quality AND Creator Equity DNA tagging."
)


async def _generate_drafts(
    artifact: dict, platforms: List[str], universe: str
) -> List[dict]:
    """Call Claude Sonnet 4.5 to draft per-platform posts. Runs in a worker thread."""
    plat_specs = "\n".join(
        f"- {p}: voice={PLATFORMS[p]['voice']} | char_limit={PLATFORMS[p]['char_limit']}"
        for p in platforms
        if p in PLATFORMS
    )
    universe_spec = UNIVERSES[universe]
    is_audio = artifact.get("category") == "music"

    user_msg = (
        f"Artifact: {artifact['title']}\n"
        f"Category: {artifact['category']}\n"
        f"Description: {artifact.get('description', '')}\n"
        f"User Vision: {artifact.get('prompt', '')}\n\n"
        f"Universe: {universe_spec['label']}\n"
        f"Aesthetic Guardrails: {universe_spec['aesthetic']}\n"
        f"Narrative Pillars: {universe_spec['narrative']}\n\n"
        f"Generate one draft per platform:\n{plat_specs}\n\n"
        f"Audio brief required: {'YES — this is a music artifact, lead with 48kHz + Creator Equity DNA' if is_audio else 'NO — leave audio_brief as empty string'}\n"
        "Captions must respect each platform's char_limit. Mockup briefs are art-direction prose, not pixel specs."
    )

    session_id = f"amp-{uuid.uuid4()}"

    async def _call_claude_draft(prompt_text: str, sys_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": EMERGENT_LLM_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-4-5-20250929", "max_tokens": 2048, "system": sys_prompt, "messages": [{"role": "user", "content": prompt_text}]},
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]

    raw = await _call_claude_draft(user_msg, DRAFT_SYSTEM_PROMPT)
    data = _extract_json(raw)
    return data.get("drafts") or []


# ---------- Nano Banana mockup rendering ----------
UNIVERSE_IMAGE_SUFFIX = {
    "cultura": (
        "High-fidelity photorealistic product mockup. Dark charcoal canvas (#0a0a0a). "
        "Brushed chrome accents, candy apple red (#C8102E) highlights used sparingly. "
        "Minimalist geometric layout. 16:9 aspect ratio. Cinematic side lighting. No text, "
        "no logos, no watermarks. Pure product shot, gallery quality."
    ),
    "nothing": (
        "Minimalist photorealistic product mockup in the style of Nothing. "
        "Transparent/translucent surfaces revealing internal components. Dot-matrix typography "
        "where text appears. Stark white-on-black palette. Candy apple red (#C8102E) ONLY on "
        "tiny LED accent points. Essentialism. Generous negative space. 16:9 aspect. No logos."
    ),
}


def _build_image_prompt(mockup_brief: str, universe: str, platform: str) -> str:
    universe_note = UNIVERSE_IMAGE_SUFFIX.get(universe, UNIVERSE_IMAGE_SUFFIX["cultura"])
    return (
        f"{mockup_brief.strip()}\n\n"
        f"Universe: {UNIVERSES[universe]['label']}. {universe_note}\n"
        f"Target platform: {PLATFORMS[platform]['label']} — visual should feel native to the feed."
    )


async def _render_mockup_png(brief: str, universe: str, platform: str) -> Optional[bytes]:
    """Render a PNG for a single draft via Gemini Nano Banana. Runs in a thread."""
    if not brief:
        return None
    prompt = _build_image_prompt(brief, universe, platform)
    session_id = f"amp-img-{uuid.uuid4()}"

    # Gemini multimodal image generation pending direct Gemini API integration
    logger.info("Nano Banana render requested for %s/%s (multimodal stubbed)", universe, platform)
    return None

    if not images:
        return None
    img = images[0]
    try:
        import base64 as _b64

        return _b64.b64decode(img["data"])
    except Exception:
        return None


async def _render_all_mockups(draft_ids_with_briefs: List[Tuple[str, str, str, str]]) -> None:
    """Background task: render every draft's mockup in parallel and persist."""
    async def _one(draft_id: str, brief: str, universe: str, platform: str):
        png = await _render_mockup_png(brief, universe, platform)
        import base64 as _b64

        if png:
            await db.drafts.update_one(
                {"id": draft_id},
                {
                    "$set": {
                        "mockup_png_b64": _b64.b64encode(png).decode("ascii"),
                        "mockup_bytes": len(png),
                        "mockup_ready": True,
                        "mockup_rendered_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
        else:
            await db.drafts.update_one(
                {"id": draft_id},
                {"$set": {"mockup_ready": True, "mockup_failed": True}},
            )

    await asyncio.gather(
        *[_one(did, brief, uni, plat) for (did, brief, uni, plat) in draft_ids_with_briefs],
        return_exceptions=True,
    )


@api.post("/drafts/generate")
async def drafts_generate(payload: DraftGenerateIn, user: dict = Depends(current_user)):
    artifact = await db.artifacts.find_one(
        {"id": payload.artifact_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    bad = [p for p in payload.platforms if p not in PLATFORMS]
    if bad:
        raise HTTPException(status_code=400, detail=f"Unknown platforms: {bad}")

    try:
        raw_drafts = await _generate_drafts(artifact, payload.platforms, payload.universe)
    except Exception as exc:
        logger.exception("Amplifier draft generation failed")
        raise HTTPException(status_code=502, detail=f"Amplifier failed: {exc}") from exc

    persisted: List[dict] = []
    to_render: List[Tuple[str, str, str, str]] = []
    now = datetime.now(timezone.utc).isoformat()
    for d in raw_drafts:
        if not isinstance(d, dict) or d.get("platform") not in PLATFORMS:
            continue
        passed, flags = soulfire_filter(d)
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "artifact_id": artifact["id"],
            "artifact_title": artifact["title"],
            "platform": d["platform"],
            "universe": payload.universe,
            "caption": str(d.get("caption", "")).strip(),
            "hashtags": list(d.get("hashtags") or [])[:8],
            "mockup_brief": str(d.get("mockup_brief", "")).strip(),
            "audio_brief": str(d.get("audio_brief", "")).strip(),
            "alt_text": str(d.get("alt_text", "")).strip(),
            "soulfire_passed": passed,
            "soulfire_flags": flags,
            "status": "needs_review" if not passed else "drafted",
            "mockup_ready": False,
            "created_at": now,
        }
        await db.drafts.insert_one(doc)
        # Persisted echo (without the heavy _id / png fields)
        persisted.append({k: v for k, v in doc.items() if k != "_id"})
        if doc["mockup_brief"]:
            to_render.append((doc["id"], doc["mockup_brief"], doc["universe"], doc["platform"]))

    # Spawn background mockup rendering — response returns instantly, images arrive async.
    if to_render:
        asyncio.create_task(_render_all_mockups(to_render))

    return {"drafts": persisted, "rendering": len(to_render)}


@api.get("/drafts")
async def list_drafts(user: dict = Depends(current_user)):
    cursor = db.drafts.find(
        {"user_id": user["id"]},
        {"_id": 0, "mockup_png_b64": 0},
    ).sort("created_at", -1)
    return [d async for d in cursor]


@api.get("/drafts/{draft_id}")
async def get_draft(draft_id: str, user: dict = Depends(current_user)):
    doc = await db.drafts.find_one(
        {"id": draft_id, "user_id": user["id"]},
        {"_id": 0, "mockup_png_b64": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Draft not found")
    return doc


@api.get("/drafts/{draft_id}/mockup.png")
async def get_draft_mockup(
    draft_id: str,
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

    doc = await db.drafts.find_one(
        {"id": draft_id, "user_id": user_id},
        {"_id": 0, "mockup_png_b64": 1, "mockup_ready": 1},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not doc.get("mockup_png_b64"):
        raise HTTPException(status_code=404, detail="Mockup not ready")

    import base64 as _b64

    png = _b64.b64decode(doc["mockup_png_b64"])
    return StreamingResponse(
        io.BytesIO(png),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@api.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str, user: dict = Depends(current_user)):
    res = await db.drafts.find_one_and_update(
        {"id": draft_id, "user_id": user["id"]},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Draft not found")
    return res


@api.post("/drafts/{draft_id}/mockup/regenerate")
async def regenerate_mockup(draft_id: str, user: dict = Depends(current_user)):
    doc = await db.drafts.find_one(
        {"id": draft_id, "user_id": user["id"]},
        {"_id": 0, "id": 1, "mockup_brief": 1, "universe": 1, "platform": 1},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not doc.get("mockup_brief"):
        raise HTTPException(status_code=400, detail="Draft has no mockup brief to render")

    # Flip to rendering state; background task will flip it back.
    await db.drafts.update_one(
        {"id": draft_id},
        {
            "$set": {"mockup_ready": False},
            "$unset": {"mockup_failed": "", "mockup_png_b64": "", "mockup_bytes": ""},
        },
    )
    asyncio.create_task(
        _render_all_mockups(
            [(doc["id"], doc["mockup_brief"], doc["universe"], doc["platform"])]
        )
    )
    return {"regenerating": True, "id": draft_id}


@api.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, user: dict = Depends(current_user)):
    res = await db.drafts.delete_one({"id": draft_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"deleted": True}


@api.get("/orchestrator/config")
async def orchestrator_config():
    return {
        "platforms": [{"id": k, **{kk: vv for kk, vv in v.items()}} for k, v in PLATFORMS.items()],
        "universes": [{"id": k, **{kk: vv for kk, vv in v.items()}} for k, v in UNIVERSES.items()],
    }


# ---------- Execution Engine (sandboxed runner) ----------
EXEC_LIMITS = {
    "aprendiz": {"per_hour": 0, "concurrent": 0},
    "soulfire": {"per_hour": 10, "concurrent": 1},
    "maestro": {"per_hour": 25, "concurrent": 2},
    # Legacy aliases
    "maestro_elite": {"per_hour": 10, "concurrent": 1},
    "maestro_master": {"per_hour": 25, "concurrent": 2},
}

_exec_active: dict[str, int] = {}
_exec_cancel_events: dict[str, asyncio.Event] = {}


async def _exec_rate_check(user: dict) -> None:
    tier = _user_tier(user)
    caps = EXEC_LIMITS.get(tier, EXEC_LIMITS["aprendiz"])
    user_id = user["id"]
    if _exec_active.get(user_id, 0) >= caps["concurrent"]:
        raise HTTPException(
            status_code=429,
            detail=f"You already have {caps['concurrent']} execution(s) running.",
        )
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = await db.executions.count_documents(
        {"user_id": user_id, "created_at": {"$gte": hour_ago.isoformat()}}
    )
    if recent >= caps["per_hour"]:
        raise HTTPException(
            status_code=429,
            detail=f"Execution rate limit hit ({caps['per_hour']}/hr on {tier}).",
            headers={"X-Tier": tier, "X-Upgrade": "/billing"},
        )


@api.post("/artifacts/{artifact_id}/execute")
async def execute_artifact(artifact_id: str, user: dict = Depends(current_user)):
    artifact = await db.artifacts.find_one(
        {"id": artifact_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    plan = _exec_detect_plan(artifact["files"])
    if plan.runtime == "unsupported":
        raise HTTPException(
            status_code=400,
            detail="Unsupported runtime. Need a Python (main.py/app.py) or Node (package.json/index.js) entry point.",
        )

    await _exec_rate_check(user)

    exec_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.executions.insert_one(
        {
            "id": exec_id,
            "user_id": user["id"],
            "artifact_id": artifact_id,
            "artifact_title": artifact["title"],
            "runtime": plan.runtime,
            "entry_path": plan.entry_path,
            "status": "queued",
            "logs": [],
            "deps_exit": None,
            "run_exit": None,
            "duration_ms": None,
            "created_at": now,
            "started_at": None,
            "finished_at": None,
        }
    )

    cancel_evt = asyncio.Event()
    _exec_cancel_events[exec_id] = cancel_evt
    _exec_active[user["id"]] = _exec_active.get(user["id"], 0) + 1

    async def _on_log(stream: str, line: str) -> None:
        await db.executions.update_one(
            {"id": exec_id},
            {
                "$push": {
                    "logs": {
                        "$each": [{"t": datetime.now(timezone.utc).isoformat(), "stream": stream, "line": line}],
                        "$slice": -2000,
                    }
                }
            },
        )

    async def _runner():
        await db.executions.update_one(
            {"id": exec_id},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}},
        )
        try:
            outcome = await _exec_run_artifact(artifact["files"], _on_log, cancel_evt)
            update = {
                "status": "canceled" if cancel_evt.is_set() else outcome.final_status,
                "deps_exit": outcome.deps_exit,
                "run_exit": outcome.run_exit,
                "duration_ms": outcome.duration_ms,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.executions.update_one({"id": exec_id}, {"$set": update})
        except Exception as exc:
            logger.exception("Execution crashed")
            await db.executions.update_one(
                {"id": exec_id},
                {
                    "$set": {
                        "status": "crashed",
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "$push": {
                        "logs": {
                            "t": datetime.now(timezone.utc).isoformat(),
                            "stream": "system",
                            "line": f"[crash] {exc}",
                        }
                    },
                },
            )
        finally:
            _exec_cancel_events.pop(exec_id, None)
            if _exec_active.get(user["id"], 0) > 0:
                _exec_active[user["id"]] -= 1

    asyncio.create_task(_runner())

    return {"id": exec_id, "status": "queued", "runtime": plan.runtime, "entry_path": plan.entry_path}


@api.get("/executions/{exec_id}")
async def get_execution(exec_id: str, user: dict = Depends(current_user)):
    doc = await db.executions.find_one({"id": exec_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Execution not found")
    return doc


@api.get("/artifacts/{artifact_id}/executions")
async def list_artifact_executions(artifact_id: str, user: dict = Depends(current_user)):
    cursor = db.executions.find(
        {"artifact_id": artifact_id, "user_id": user["id"]},
        {"_id": 0, "logs": 0},
    ).sort("created_at", -1).limit(20)
    return [d async for d in cursor]


@api.post("/executions/{exec_id}/cancel")
async def cancel_execution(exec_id: str, user: dict = Depends(current_user)):
    doc = await db.executions.find_one({"id": exec_id, "user_id": user["id"]}, {"_id": 0, "id": 1, "status": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Execution not found")
    if doc["status"] not in ("queued", "running"):
        return {"canceled": False, "reason": f"already {doc['status']}"}
    evt = _exec_cancel_events.get(exec_id)
    if evt:
        evt.set()
    return {"canceled": True}


PINNED_RUNS_MAX = 5
PIN_LOG_TAIL = 200  # last N log entries kept on the pinned record


@api.post("/executions/{exec_id}/pin")
async def pin_execution(exec_id: str, user: dict = Depends(current_user)):
    """Master-tier only. Embed a trimmed run summary into the artifact's demo reel."""
    if _user_tier(user) != "maestro_master":
        raise HTTPException(
            status_code=402,
            detail="Pinned-run history is a Maestro Master feature. Upgrade to keep your demo reel.",
            headers={"X-Upgrade": "/billing", "X-Required-Tier": "maestro_master"},
        )

    ex = await db.executions.find_one({"id": exec_id, "user_id": user["id"]}, {"_id": 0})
    if not ex:
        raise HTTPException(status_code=404, detail="Execution not found")
    if ex["status"] in ("queued", "running"):
        raise HTTPException(status_code=400, detail="Execution still running — wait for it to finish")

    pinned = {
        "execution_id": ex["id"],
        "runtime": ex.get("runtime"),
        "entry_path": ex.get("entry_path"),
        "status": ex.get("status"),
        "run_exit": ex.get("run_exit"),
        "deps_exit": ex.get("deps_exit"),
        "duration_ms": ex.get("duration_ms"),
        "logs_tail": (ex.get("logs") or [])[-PIN_LOG_TAIL:],
        "pinned_at": datetime.now(timezone.utc).isoformat(),
        "ran_at": ex.get("started_at") or ex.get("created_at"),
    }

    # Atomic upsert: if this exec is already pinned, replace it; else append + cap to last MAX.
    art = await db.artifacts.find_one(
        {"id": ex["artifact_id"], "user_id": user["id"]}, {"_id": 0, "pinned_runs": 1}
    )
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    existing = art.get("pinned_runs") or []
    new_list = [p for p in existing if p.get("execution_id") != ex["id"]]
    new_list.append(pinned)
    new_list = new_list[-PINNED_RUNS_MAX:]

    await db.artifacts.update_one(
        {"id": ex["artifact_id"], "user_id": user["id"]},
        {"$set": {"pinned_runs": new_list}},
    )
    return {"pinned": True, "count": len(new_list), "execution_id": ex["id"]}


@api.delete("/artifacts/{artifact_id}/pinned/{exec_id}")
async def unpin_run(artifact_id: str, exec_id: str, user: dict = Depends(current_user)):
    res = await db.artifacts.update_one(
        {"id": artifact_id, "user_id": user["id"]},
        {"$pull": {"pinned_runs": {"execution_id": exec_id}}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"unpinned": True}


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
