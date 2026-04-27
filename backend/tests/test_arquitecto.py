"""Backend tests for El Arquitecto AI."""
import io
import os
import uuid
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://el-centro-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

UNIQUE = uuid.uuid4().hex[:8]
TEST_EMAIL = f"TEST_tester_{UNIQUE}@example.com"
TEST_PASSWORD = "forgehot123"
TEST_NAME = "Test Arquitecto"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth(session):
    r = session.post(f"{API}/auth/signup", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD, "display_name": TEST_NAME
    }, timeout=30)
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == TEST_EMAIL.lower()
    return data


# ---------- Service / categories ----------
def test_root(session):
    r = session.get(f"{API}/", timeout=15)
    assert r.status_code == 200
    assert r.json().get("service") == "El Arquitecto AI"


def test_categories(session):
    r = session.get(f"{API}/categories", timeout=15)
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert ids == {"music", "art_visual", "commerce", "community", "storytelling"}


# ---------- Auth ----------
def test_signup_duplicate(session, auth):
    r = session.post(f"{API}/auth/signup", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD, "display_name": TEST_NAME
    }, timeout=15)
    assert r.status_code == 409


def test_login_success(session, auth):
    r = session.post(f"{API}/auth/login", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD
    }, timeout=15)
    assert r.status_code == 200
    assert "token" in r.json()


def test_login_wrong(session, auth):
    r = session.post(f"{API}/auth/login", json={
        "email": TEST_EMAIL, "password": "wrongpass"
    }, timeout=15)
    assert r.status_code == 401


def test_me_with_token(session, auth):
    r = session.get(f"{API}/auth/me",
                    headers={"Authorization": f"Bearer {auth['token']}"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["email"] == TEST_EMAIL.lower()


def test_me_no_token(session):
    r = requests.get(f"{API}/auth/me", timeout=15)
    assert r.status_code == 401


# ---------- Generate artifact (requires LLM) ----------
@pytest.fixture(scope="module")
def generated_artifact(session, auth):
    r = session.post(
        f"{API}/artifacts/generate",
        json={"prompt": "Tiny music player that honors creator equity with waveform viz", "category": "music"},
        headers={"Authorization": f"Bearer {auth['token']}"},
        timeout=180,
    )
    assert r.status_code == 200, f"generate failed: {r.status_code} {r.text[:500]}"
    return r.json()


def test_generate_requires_auth(session):
    r = session.post(f"{API}/artifacts/generate",
                     json={"prompt": "hello world with enough chars", "category": "music"},
                     timeout=15)
    assert r.status_code == 401


def test_generate_artifact_structure(generated_artifact):
    a = generated_artifact
    for key in ["id", "title", "description", "category", "files", "terminal_log", "refined_prompt", "created_at"]:
        assert key in a, f"Missing {key}"
    assert a["category"] == "music"
    assert len(a["files"]) >= 1
    assert "Chicano AI Architect" in a["refined_prompt"]
    assert "48kHz" in a["refined_prompt"]
    assert "Emotional Math" in a["refined_prompt"]
    assert "Creator Equity" in a["refined_prompt"]
    assert any("forge" in line.lower() or "arquitecto" in line.lower() for line in a["terminal_log"])


def test_list_artifacts(session, auth, generated_artifact):
    r = session.get(f"{API}/artifacts",
                    headers={"Authorization": f"Bearer {auth['token']}"}, timeout=15)
    assert r.status_code == 200
    items = r.json()
    assert any(i["id"] == generated_artifact["id"] for i in items)
    assert items[0]["file_count"] >= 1


def test_get_artifact_owner(session, auth, generated_artifact):
    r = session.get(f"{API}/artifacts/{generated_artifact['id']}",
                    headers={"Authorization": f"Bearer {auth['token']}"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["id"] == generated_artifact["id"]


def test_get_artifact_other_user_404(session, generated_artifact):
    # create second user
    email2 = f"TEST_other_{uuid.uuid4().hex[:6]}@example.com"
    r = session.post(f"{API}/auth/signup",
                     json={"email": email2, "password": "abc12345", "display_name": "Other"},
                     timeout=15)
    assert r.status_code == 200
    t2 = r.json()["token"]
    r = session.get(f"{API}/artifacts/{generated_artifact['id']}",
                    headers={"Authorization": f"Bearer {t2}"}, timeout=15)
    assert r.status_code == 404


def test_download_zip_with_token_query(auth, generated_artifact):
    r = requests.get(f"{API}/artifacts/{generated_artifact['id']}/download",
                     params={"token": auth["token"]}, timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip")
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert any(n.endswith("SOULFIRE.json") for n in names)
    # Paths are prefixed with safe_title (no leading /, no ..)
    for n in names:
        assert not n.startswith("/")
        assert ".." not in n
        # Every file should be under a single top-level dir (safe_title)
        assert "/" in n, f"file {n} not under safe_title dir"


def test_download_zip_with_bearer_header(auth, generated_artifact):
    r = requests.get(f"{API}/artifacts/{generated_artifact['id']}/download",
                     headers={"Authorization": f"Bearer {auth['token']}"}, timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip")
