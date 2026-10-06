"""
Stage 7 tests — character-consistent image generation orchestration.
Follows the same in-memory-SQLite + AsyncClient pattern as test_e2e.py/
test_stage5.py (dependency override scoped to the autouse fixture, not
module-level, per the cross-test-leak fix earlier in this build). ComfyUI's
health check is mocked to always report unhealthy, so these stay fast and
deterministic and always exercise the Pillow-fallback path — the only path
this environment (no ComfyUI, no GPU) can actually verify live; the real
ComfyUI path is exercised structurally in test_comfy_workflow_builder.py.
"""
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db
from app import models

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _seed_project_scene_shot(session, characters=None):
    project = models.Project(user_id="u1", title="T")
    session.add(project)
    await session.flush()

    scene = models.Scene(
        project_id=project.id, scene_number=1, heading="INT. ROOM - DAY",
        characters_present=json.dumps([c["name"] for c in (characters or [])]),
        visual_emphasis="Test emphasis.",
    )
    session.add(scene)
    await session.flush()

    for c in (characters or []):
        session.add(models.Character(
            project_id=project.id, name=c["name"], description=c.get("description", ""),
            is_locked=1 if c.get("is_locked", True) else 0,
            reference_image_paths=json.dumps(c.get("reference_image_paths", ["/static/character_refs/x.png"])),
        ))

    shot = models.Shot(
        scene_id=scene.id, shot_number=1, shot_size="Medium", angle="Eye Level",
        characters_in_shot=json.dumps([c["name"] for c in (characters or [])]) if characters is not None else None,
    )
    session.add(shot)
    await session.commit()
    await session.refresh(shot)
    return project, scene, shot


@pytest.mark.asyncio
async def test_generate_image_no_characters_uses_placeholder_fallback(client):
    async with TestSessionLocal() as session:
        _, _, shot = await _seed_project_scene_shot(session, characters=[])

    with patch("app.comfy_client.ComfyClient.is_healthy", new=AsyncMock(return_value=False)):
        resp = await client.post(f"/api/shots/{shot.id}/generate-image")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["image_url"].startswith("/static/storyboards/")

@pytest.mark.asyncio
async def test_generate_image_locked_single_character_succeeds(client):
    async with TestSessionLocal() as session:
        _, _, shot = await _seed_project_scene_shot(session, characters=[
            {"name": "Vasanth", "is_locked": True},
        ])

    with patch("app.comfy_client.ComfyClient.is_healthy", new=AsyncMock(return_value=False)):
        resp = await client.post(f"/api/shots/{shot.id}/generate-image")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

@pytest.mark.asyncio
async def test_generate_image_unlocked_character_returns_400(client):
    async with TestSessionLocal() as session:
        _, _, shot = await _seed_project_scene_shot(session, characters=[
            {"name": "Vasanth", "is_locked": False},
        ])

    resp = await client.post(f"/api/shots/{shot.id}/generate-image")
    assert resp.status_code == 400
    assert "not yet locked" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_generate_image_missing_shot_returns_404(client):
    resp = await client.post("/api/shots/nonexistent-id/generate-image")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_storyboards_alias_route_runs_same_pipeline(client):
    """POST /storyboards/{shot_id}/generate (what the frontend calls) must
    behave identically to the spec-literal /shots/{id}/generate-image."""
    async with TestSessionLocal() as session:
        _, _, shot = await _seed_project_scene_shot(session, characters=[])

    with patch("app.comfy_client.ComfyClient.is_healthy", new=AsyncMock(return_value=False)):
        resp = await client.post(f"/api/storyboards/{shot.id}/generate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

@pytest.mark.asyncio
async def test_generate_image_falls_back_to_scene_cast_when_shot_field_unset(client):
    """Shots created before Stage 4/5 populated characters_in_shot
    (characters_in_shot is None, not '[]') must still resolve characters
    from the scene's cast rather than crash."""
    async with TestSessionLocal() as session:
        project = models.Project(user_id="u1", title="T")
        session.add(project)
        await session.flush()
        scene = models.Scene(
            project_id=project.id, scene_number=1, heading="INT. ROOM - DAY",
            characters_present=json.dumps(["Vasanth"]),
        )
        session.add(scene)
        await session.flush()
        session.add(models.Character(
            project_id=project.id, name="Vasanth", is_locked=1,
            reference_image_paths=json.dumps(["/static/character_refs/x.png"]),
        ))
        shot = models.Shot(scene_id=scene.id, shot_number=1, characters_in_shot=None)
        session.add(shot)
        await session.commit()
        await session.refresh(shot)

    with patch("app.comfy_client.ComfyClient.is_healthy", new=AsyncMock(return_value=False)):
        resp = await client.post(f"/api/shots/{shot.id}/generate-image")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


# ── Focal-character reference conditioning ──────────────────────────────────
# Regression tests for the confirmed cross-character reference-blending bug:
# pooling every present character's reference into one ReferenceLatent chain
# put SITA's braid and saree colours onto RAM in every shot they shared.

from app.stage7_orchestrator import _select_focal_character


class _FakeShot:
    def __init__(self, composition_notes=None, framing=None, reasoning=None, notes=None):
        self.composition_notes = composition_notes
        self.framing = framing
        self.reasoning = reasoning
        self.notes = notes


class _FakeChar:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"<{self.name}>"


def test_focal_character_single_character_is_trivially_focal():
    ram = _FakeChar("RAM")
    assert _select_focal_character(_FakeShot(), [ram]) is ram

def test_focal_character_prefers_composition_notes_subject():
    ram, sita = _FakeChar("RAM"), _FakeChar("SITA")
    # composition_notes names the actual subject of the frame
    shot = _FakeShot(composition_notes="Close, Sita's face, eyes lowered",
                      reasoning="Tracks Ram as he watches Sita")
    assert _select_focal_character(shot, [ram, sita]) is sita

def test_focal_character_falls_back_to_reasoning_first_mention():
    ram, sita = _FakeChar("RAM"), _FakeChar("SITA")
    shot = _FakeShot(reasoning="Tracks Ram as he watches Sita across the aisle")
    assert _select_focal_character(shot, [ram, sita]) is ram
    shot2 = _FakeShot(reasoning="Frames Sita's reaction to Ram, emphasizing her glance")
    assert _select_focal_character(shot2, [ram, sita]) is sita

def test_focal_character_falls_back_to_shot_order_when_unnamed():
    ram, sita = _FakeChar("RAM"), _FakeChar("SITA")
    shot = _FakeShot(reasoning="Establishes the train compartment setting and time of day")
    assert _select_focal_character(shot, [ram, sita]) is ram


# ── Two-person verification gate ───────────────────────────────────────────
from app.stage7_orchestrator import _requires_multiple_people


def test_requires_multiple_people_only_when_two_plus_present():
    assert _requires_multiple_people("Two-Shot", 1) is False
    assert _requires_multiple_people("Medium", 1) is False

def test_requires_multiple_people_for_subject_framed_shots():
    for size in ("Two-Shot", "Medium", "Medium Close-Up", "Over-the-Shoulder", "Close-Up"):
        assert _requires_multiple_people(size, 2) is True, size

def test_requires_multiple_people_skips_wide_and_detail_shots():
    """An establishing wide of a mountain outpost or an insert of a letter
    shouldn't be retried for 'not enough faces' -- the characters are
    incidental scenery there, not the subject."""
    for size in ("Wide Shot", "Extreme Wide Shot", "Establishing Shot", "Insert", "Cutaway", "Aerial"):
        assert _requires_multiple_people(size, 2) is False, size

def test_requires_multiple_people_handles_missing_shot_size():
    assert _requires_multiple_people(None, 2) is True   # unknown size -> treat as a framed shot
    assert _requires_multiple_people("", 2) is True


def test_face_gate_skips_wide_and_detail_shots():
    from app.stage7_orchestrator import _face_gate_applies
    assert _face_gate_applies("Medium Shot") and _face_gate_applies("Close-Up") and _face_gate_applies("Two-Shot")
    assert not _face_gate_applies("Wide Shot") and not _face_gate_applies("Insert")


def test_weak_faces_flags_only_faces_below_the_gate(monkeypatch):
    from app import stage7_orchestrator as so
    monkeypatch.setattr(so.face_identity, "identity_scores", lambda img, refs, prio: {"RAM": 0.45, "SITA": 0.79})
    assert so._weak_faces("x.png", {"RAM": [1], "SITA": [1]}, ["RAM", "SITA"]) == {"RAM": 0.45}
    assert so._weak_faces("x.png", {}, ["RAM"]) == {}
