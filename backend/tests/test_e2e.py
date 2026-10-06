"""
Module 38: End-to-End Workflow Verification
Tests the complete lifecycle: Project → Story → Character → Scene → Shot → Storyboard → Export
Uses an in-memory SQLite DB and mock auth (no API keys required).
"""
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from app.main import app
from app.database import Base, get_db

# ─── In-memory test database ────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

MOCK_TOKEN = "mock_vasu_token_xyz"
AUTH_HEADERS = {"Authorization": f"Bearer {MOCK_TOKEN}"}

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after. The get_db override is
    scoped to this fixture too (not module-level) so it can't leak into
    other test files that share the same `app` singleton and expect the
    real database engine (e.g. test_api.py, test_production.py)."""
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


# ════════════════════════════════════════════════════════════════════════════
# MODULE 38 — FULL E2E WORKFLOW
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e2e_full_workflow(client):
    """
    Full lifecycle test:
    Create Project → Update Story → Add Character → Parse Screenplay →
    Create Shot → Generate Storyboard Frame → Export PDF → Verify Version
    """

    # ── STEP 1: Create Project ──────────────────────────────────────────────
    create_resp = await client.post("/api/projects/", json={
        "title": "E2E Test Film",
        "logline": "A test story about testing.",
        "premise": "In a world of tests...",
        "synopsis": "A comprehensive E2E verification.",
    }, headers=AUTH_HEADERS)
    assert create_resp.status_code == 201, f"Create project failed: {create_resp.text}"
    project = create_resp.json()
    project_id = project["id"]
    assert project["title"] == "E2E Test Film"

    # ── STEP 2: Update Project with Story Engine output ─────────────────────
    update_resp = await client.put(f"/api/projects/{project_id}", json={
        "logline": "A visionary director chases an impossible film across three continents.",
        "beat_sheet": json.dumps(["Opening Image", "Theme Stated", "Set Up", "Catalyst"]),
        "themes": json.dumps(["obsession", "art", "sacrifice"]),
        "conflicts": json.dumps(["Man vs Nature", "Man vs Self"]),
    }, headers=AUTH_HEADERS)
    assert update_resp.status_code == 200, f"Update project failed: {update_resp.text}"
    updated = update_resp.json()
    assert "obsession" in updated["themes"]

    # ── STEP 3: Create Character ─────────────────────────────────────────────
    char_resp = await client.post(f"/api/characters/?project_id={project_id}", json={
        "name": "MARCO VISCONTI",
        "description": "An Italian auteur director with a tragic past.",
        "traits": json.dumps(["Obsessive", "Brilliant", "Self-destructive"]),
        "age": 52,
        "motivation": "Create the perfect film before he dies.",
        "fear": "Mediocrity",
        "backstory": "Started as a street photographer in Rome.",
        "personality": "Intense and charismatic"
    }, headers=AUTH_HEADERS)
    assert char_resp.status_code == 201, f"Create character failed: {char_resp.text}"
    character = char_resp.json()
    char_id = character["id"]
    assert character["name"] == "MARCO VISCONTI"

    # ── STEP 4: Update Character (Bible enrichment) ──────────────────────────
    char_update_resp = await client.put(f"/api/characters/{char_id}", json={
        "weakness": "Perfectionism that paralyzes production",
        "relationships": json.dumps({"friend": ["LUCIA"], "rival": ["THE STUDIO EXEC"]})
    }, headers=AUTH_HEADERS)
    assert char_update_resp.status_code == 200
    updated_char = char_update_resp.json()
    assert "Perfectionism" in updated_char["weakness"]

    # ── STEP 5: Verify project now shows character ───────────────────────────
    get_resp = await client.get(f"/api/projects/{project_id}", headers=AUTH_HEADERS)
    assert get_resp.status_code == 200
    proj_data = get_resp.json()
    assert len(proj_data["characters"]) == 1
    assert proj_data["characters"][0]["name"] == "MARCO VISCONTI"

    # ── STEP 6: Parse Screenplay (inject raw screenplay text) ───────────────
    screenplay_text = b"""INT. CRUMBLING CINEMA - NIGHT

MARCO stands alone in the empty theatre. A single projector beam cuts the darkness.

MARCO
(whispering)
This is where it all ends. Or begins.

He presses PLAY. The screen flickers to life.

EXT. ROMAN STREETS - DAY

A younger MARCO chases pigeons with his camera. Joy on his face."""

    import io
    parse_resp = await client.post(
        f"/api/projects/{project_id}/parse",
        files={"file": ("screenplay.fountain", io.BytesIO(screenplay_text), "text/plain")},
        headers=AUTH_HEADERS
    )
    assert parse_resp.status_code == 200, f"Parse screenplay failed: {parse_resp.text}"
    parsed_proj = parse_resp.json()
    assert len(parsed_proj["scenes"]) >= 2, "Expected at least 2 parsed scenes"

    # ── STEP 7: Get Scenes list ──────────────────────────────────────────────
    scenes_resp = await client.get(f"/api/scenes/?project_id={project_id}")
    assert scenes_resp.status_code == 200
    scenes = scenes_resp.json()
    assert len(scenes) >= 2
    scene_id = scenes[0]["id"]

    # ── STEP 7.5: Lock the character's reference (Stage 6) ───────────────────
    # /parse replaces characters with whatever the screenplay itself names
    # (here: "MARCO", the dialogue-cue name — not "MARCO VISCONTI" from step
    # 3, which parsing supersedes). Stage 6's hard rule blocks image
    # generation for any named character until it's locked, so lock it here
    # exactly as a real user of this pipeline would have to.
    chars_resp = await client.get(f"/api/characters/?project_id={project_id}", headers=AUTH_HEADERS)
    assert chars_resp.status_code == 200
    parsed_characters = chars_resp.json()
    assert len(parsed_characters) >= 1
    marco = next(c for c in parsed_characters if c["name"].upper() == "MARCO")
    lock_resp = await client.post(f"/api/characters/{marco['id']}/lock-reference", headers=AUTH_HEADERS)
    assert lock_resp.status_code == 200, f"Lock reference failed: {lock_resp.text}"
    assert lock_resp.json()["is_locked"] == 1

    # ── STEP 8: Create a Shot for the first scene ────────────────────────────
    shot_resp = await client.post(f"/api/shots/?scene_id={scene_id}", json={
        "shot_number": 1,
        "shot_size": "CU",
        "angle": "Eye Level",
        "movement": "Static",
        "lens": "85mm",
        "lighting": "Low Key",
        "emotion": "Despair",
        "color_palette": "Desaturated Blues",
        "notes": "Marco's face lit by projector beam, tears on cheek.",
        "order": 0,
        "day_night": "Night",
        "duration": 4,
        "status": "Pending"
    })
    assert shot_resp.status_code == 201, f"Create shot failed: {shot_resp.text}"
    shot = shot_resp.json()
    shot_id = shot["id"]
    assert shot["shot_size"] == "CU"
    assert shot["emotion"] == "Despair"

    # ── STEP 9: Generate Storyboard Frame ────────────────────────────────────
    storyboard_resp = await client.post(f"/api/storyboards/{shot_id}/generate")
    assert storyboard_resp.status_code == 200, f"Storyboard gen failed: {storyboard_resp.text}"
    frame = storyboard_resp.json()
    assert frame["shot_id"] == shot_id
    assert frame["status"] in ("completed", "failed", "pending")  # accept any (no GPU in CI)
    assert frame["prompt"] is not None  # prompt was built

    # ── STEP 10: Verify storyboard appears on project storyboard list ────────
    sb_list_resp = await client.get(f"/api/storyboards/project/{project_id}")
    assert sb_list_resp.status_code == 200
    frames = sb_list_resp.json()
    assert len(frames) >= 1

    # ── STEP 11: Update shot with Director's Muse result ────────────────────
    shot_update_resp = await client.put(f"/api/shots/{shot_id}", json={
        "visual_tip": "Inspired by Villeneuve — isolate subject in vast negative space.",
        "color_palette": "Amber on Black",
        "lighting": "Motivated Candlelight"
    })
    assert shot_update_resp.status_code == 200
    updated_shot = shot_update_resp.json()
    assert "Villeneuve" in updated_shot["visual_tip"]

    # ── STEP 12: Duplicate Project (version snapshot) ────────────────────────
    dup_resp = await client.post(f"/api/projects/{project_id}/duplicate", headers=AUTH_HEADERS)
    assert dup_resp.status_code == 200, f"Duplicate project failed: {dup_resp.text}"
    dup_proj = dup_resp.json()
    assert "(Copy)" in dup_proj["title"]
    assert dup_proj["id"] != project_id

    # ── STEP 13: Export CSV ──────────────────────────────────────────────────
    csv_resp = await client.get(f"/api/projects/{project_id}/export/csv", headers=AUTH_HEADERS)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    csv_content = csv_resp.text
    assert "CU" in csv_content  # shot size appears in export

    # ── STEP 14: Export PDF ──────────────────────────────────────────────────
    pdf_resp = await client.get(f"/api/projects/{project_id}/export/pdf", headers=AUTH_HEADERS)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers.get("content-type") == "application/pdf"
    assert len(pdf_resp.content) > 100  # non-empty PDF

    # ── STEP 15: Soft-delete project ─────────────────────────────────────────
    delete_resp = await client.delete(f"/api/projects/{project_id}", headers=AUTH_HEADERS)
    assert delete_resp.status_code == 204

    # ── STEP 16: Verify it's gone from list ──────────────────────────────────
    list_resp = await client.get("/api/projects/", headers=AUTH_HEADERS)
    assert list_resp.status_code == 200
    remaining = [p for p in list_resp.json() if p["id"] == project_id]
    assert len(remaining) == 0, "Deleted project should not appear in list"

    print("✅ E2E Full Workflow PASSED — 16 steps verified successfully.")


# ════════════════════════════════════════════════════════════════════════════
# MODULE 39 — INTER-MODULE COMMUNICATION TESTS
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_project_character_relationship_cascade(client):
    """Characters are properly linked to project and cascade on project ops."""
    # Create project
    proj = (await client.post("/api/projects/", json={"title": "Cascade Test"}, headers=AUTH_HEADERS)).json()
    pid = proj["id"]

    # Add 3 characters
    for name in ["ELENA", "DMITRI", "SASHA"]:
        resp = await client.post(f"/api/characters/?project_id={pid}", json={"name": name})
        assert resp.status_code == 201

    # Verify all 3 appear in project details
    proj_detail = (await client.get(f"/api/projects/{pid}", headers=AUTH_HEADERS)).json()
    assert len(proj_detail["characters"]) == 3

    # Duplicate — copies all 3 characters
    dup = (await client.post(f"/api/projects/{pid}/duplicate", headers=AUTH_HEADERS)).json()
    dup_detail = (await client.get(f"/api/projects/{dup['id']}", headers=AUTH_HEADERS)).json()
    assert len(dup_detail["characters"]) == 3


@pytest.mark.asyncio
async def test_scene_shot_storyboard_chain(client):
    """Scene → Shot → Storyboard chain flows without orphan records."""
    import io
    proj = (await client.post("/api/projects/", json={"title": "Chain Test"}, headers=AUTH_HEADERS)).json()
    pid = proj["id"]

    # Parse screenplay to create scene
    text = b"INT. LAB - DAY\n\nSCIENTIST enters wearing goggles."
    parse_resp = await client.post(
        f"/api/projects/{pid}/parse",
        files={"file": ("script.fountain", io.BytesIO(text), "text/plain")},
        headers=AUTH_HEADERS
    )
    assert parse_resp.status_code == 200
    scenes = (await client.get(f"/api/scenes/?project_id={pid}")).json()
    assert len(scenes) >= 1
    scene_id = scenes[0]["id"]

    # Create shot
    shot = (await client.post(f"/api/shots/?scene_id={scene_id}", json={
        "shot_number": 1, "shot_size": "WS", "angle": "High"
    })).json()
    sid = shot["id"]

    # Generate storyboard
    frame = (await client.post(f"/api/storyboards/{sid}/generate")).json()
    assert frame["shot_id"] == sid

    # Verify chain on storyboard list
    frames = (await client.get(f"/api/storyboards/project/{pid}")).json()
    assert any(f["shot_id"] == sid for f in frames)


@pytest.mark.asyncio
async def test_scene_reorder_and_continuity(client):
    """Scene reordering works and continuity validation endpoint responds."""
    import io
    proj = (await client.post("/api/projects/", json={"title": "Reorder Test"}, headers=AUTH_HEADERS)).json()
    pid = proj["id"]

    text = b"""INT. ROOM A - DAY
A enters.

INT. ROOM B - NIGHT
B exits."""

    await client.post(
        f"/api/projects/{pid}/parse",
        files={"file": ("s.fountain", io.BytesIO(text), "text/plain")},
        headers=AUTH_HEADERS
    )
    scenes = (await client.get(f"/api/scenes/?project_id={pid}")).json()
    assert len(scenes) >= 2

    ids = [s["id"] for s in scenes]
    # Reverse order
    reorder_resp = await client.post("/api/scenes/reorder", json={"ids": list(reversed(ids))})
    assert reorder_resp.status_code == 204

    # Continuity check endpoint
    cont_resp = await client.post(f"/api/scenes/{ids[0]}/validate-continuity")
    assert cont_resp.status_code == 200
    assert "warnings" in cont_resp.json()


@pytest.mark.asyncio
async def test_search_endpoint_cross_project(client):
    """Search endpoint returns results across multiple projects."""
    for title in ["Noir Dreams", "Desert Mirage", "Arctic Silence"]:
        await client.post("/api/projects/", json={"title": title, "logline": f"A story about {title.lower()}"}, headers=AUTH_HEADERS)

    search_resp = await client.get("/api/search/?q=dreams", headers=AUTH_HEADERS)
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert isinstance(results, (dict, list))


@pytest.mark.asyncio
async def test_shot_batch_update(client):
    """Batch shot updates apply to all specified shots."""
    import io
    proj = (await client.post("/api/projects/", json={"title": "Batch Test"}, headers=AUTH_HEADERS)).json()
    pid = proj["id"]
    text = b"INT. STUDIO - DAY\nCameras everywhere."
    await client.post(f"/api/projects/{pid}/parse",
        files={"file": ("s.fountain", io.BytesIO(text), "text/plain")}, headers=AUTH_HEADERS)
    scenes = (await client.get(f"/api/scenes/?project_id={pid}")).json()
    scene_id = scenes[0]["id"]

    shot_ids = []
    for n in [1, 2, 3]:
        s = (await client.post(f"/api/shots/?scene_id={scene_id}", json={"shot_number": n, "shot_size": "MS"})).json()
        shot_ids.append(s["id"])

    batch_resp = await client.put("/api/shots/batch", json={
        "ids": shot_ids,
        "updates": {"status": "Approved", "day_night": "Night"}
    })
    assert batch_resp.status_code == 200
    updated = batch_resp.json()
    for shot in updated:
        assert shot["status"] == "Approved"
        assert shot["day_night"] == "Night"


@pytest.mark.asyncio
async def test_compose_boards_drafts_missing_captions_and_returns_png_and_pdf(client, monkeypatch):
    """Stage 8 end to end through the API the 'Compose Boards' button calls."""
    import io, json, os
    from unittest.mock import AsyncMock
    from app import ai_service, board_service

    proj = (await client.post("/api/projects/", json={"title": "Board Test"}, headers=AUTH_HEADERS)).json()
    pid = proj["id"]
    await client.post(f"/api/projects/{pid}/parse", headers=AUTH_HEADERS,
                      files={"file": ("s.fountain", io.BytesIO(b"INT. LAB - DAY\n\nANNA enters.\n\nANNA\nHello."), "text/plain")})
    scene_id = (await client.get(f"/api/scenes/?project_id={pid}")).json()[0]["id"]
    kept = (await client.post(f"/api/shots/?scene_id={scene_id}", json={
        "shot_number": 1, "shot_size": "Wide Shot", "board_caption": "My own caption."})).json()
    drafted = (await client.post(f"/api/shots/?scene_id={scene_id}", json={"shot_number": 2, "shot_size": "Close-Up"})).json()
    await client.put(f"/api/projects/{pid}", headers=AUTH_HEADERS,
                     json={"board_legend_settings": json.dumps({"tagline": "A test tagline"})})

    draft = AsyncMock(return_value={2: {"caption": "Anna walks in.", "dialogue": "ANNA: “Hello.”"}})
    monkeypatch.setattr(ai_service, "draft_board_captions", draft)
    resp = await client.post(f"/api/projects/{pid}/boards/compose", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    boards = resp.json()
    try:
        assert len(boards) == 1 and boards[0]["page_range_label"] == "1 OF 1"
        for key in ("output_image_path", "output_pdf_path"):
            assert os.path.exists(os.path.join(board_service.BACKEND_ROOT, boards[0][key].lstrip("/")))
        # only the shot WITHOUT a caption was sent to the drafter; both are saved
        sent = draft.await_args.args[2]
        assert [s["shot_number"] for s in sent] == [2]
        assert (await client.get(f"/api/shots/{kept['id']}")).json()["board_caption"] == "My own caption."
        saved = (await client.get(f"/api/shots/{drafted['id']}")).json()
        assert saved["board_caption"] == "Anna walks in." and saved["board_dialogue"] == "ANNA: “Hello.”"
    finally:
        for b in boards:
            for key in ("output_image_path", "output_pdf_path"):
                path = os.path.join(board_service.BACKEND_ROOT, b[key].lstrip("/"))
                if os.path.exists(path):
                    os.remove(path)
