"""
Module 47: Comprehensive Test Suite
Tests for Agents, Copilot, Script Doctor, Middleware, and Parser.
"""
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

# ─── In-memory DB setup ──────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db

MOCK_TOKEN = "mock_vasu_token_xyz"
AUTH_HEADERS = {"Authorization": f"Bearer {MOCK_TOKEN}"}

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ════════════════════════════════════════════════════════════════════════════
# AGENT COORDINATOR TESTS (Module 40)
# ════════════════════════════════════════════════════════════════════════════

def test_agent_memory_creation():
    from app.agent_coordinator import get_or_create_memory, clear_memory
    pid = "test_proj_001"
    clear_memory(pid)
    mem = get_or_create_memory(pid, project_title="Test Film", genre="Thriller")
    assert mem.project_id == pid
    assert mem.project_title == "Test Film"
    assert mem.genre == "Thriller"
    clear_memory(pid)


def test_agent_memory_context_string():
    from app.agent_coordinator import get_or_create_memory, clear_memory
    pid = "test_proj_002"
    clear_memory(pid)
    mem = get_or_create_memory(pid, project_title="Noir City", director_style="Kubrick", genre="Noir")
    mem.themes = ["identity", "corruption"]
    ctx = mem.to_context_string()
    assert "Noir City" in ctx
    assert "Kubrick" in ctx
    assert "identity" in ctx
    clear_memory(pid)


def test_agent_memory_conversation_history():
    from app.agent_coordinator import get_or_create_memory, clear_memory
    pid = "test_proj_003"
    clear_memory(pid)
    mem = get_or_create_memory(pid)
    for i in range(25):
        mem.add_conversation_turn("story", f"input {i}", f"output {i}")
    # Should cap at 20 turns
    assert len(mem.conversation_history) == 20
    assert mem.conversation_history[0]["user"] == "input 5"
    clear_memory(pid)


def test_agent_memory_update():
    from app.agent_coordinator import get_or_create_memory, update_memory, clear_memory
    pid = "test_proj_004"
    clear_memory(pid)
    get_or_create_memory(pid, director_style="Nolan")
    updated = update_memory(pid, director_style="Villeneuve", genre="Sci-Fi")
    assert updated.director_style == "Villeneuve"
    assert updated.genre == "Sci-Fi"
    clear_memory(pid)


# ════════════════════════════════════════════════════════════════════════════
# CINEMATIC COPILOT TESTS (Module 41)
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_copilot_dialogue_detection():
    from app.copilot_engine import CinematicCopilot
    copilot = CinematicCopilot()
    result = await copilot.suggest("ELENA says she never trusted anyone before.")
    assert result["scene_type"] == "dialogue"
    assert "camera_suggestions" in result
    assert "blocking_suggestions" in result
    assert len(result["camera_suggestions"]) > 0


@pytest.mark.asyncio
async def test_copilot_action_detection():
    from app.copilot_engine import CinematicCopilot
    copilot = CinematicCopilot()
    result = await copilot.suggest("MARCO runs through the burning building.")
    assert result["scene_type"] == "action"
    assert "emotion_enhancement" in result


@pytest.mark.asyncio
async def test_copilot_emotion_detection():
    from app.copilot_engine import CinematicCopilot
    copilot = CinematicCopilot()
    # grief keywords
    result = await copilot.suggest("She weeps over his grave. The loss is unbearable.")
    assert result["detected_emotion"] == "grief"
    assert result["emotion_enhancement"] != ""


@pytest.mark.asyncio
async def test_copilot_director_note():
    from app.copilot_engine import CinematicCopilot
    from app.agent_coordinator import get_or_create_memory, clear_memory
    pid = "copilot_test_001"
    clear_memory(pid)
    mem = get_or_create_memory(pid, director_style="Kubrick")
    copilot = CinematicCopilot()
    result = await copilot.suggest("The character walks alone through the corridor.", memory=mem)
    assert "symmetr" in result["director_note"].lower() or "one-point" in result["director_note"].lower()
    clear_memory(pid)


@pytest.mark.asyncio
async def test_copilot_api_endpoint(client):
    resp = await client.post("/api/copilot/suggest", json={
        "scene_fragment": "She whispers goodbye and walks into the rain.",
        "project_id": None
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "camera_suggestions" in data
    assert "scene_type" in data


# ════════════════════════════════════════════════════════════════════════════
# SCRIPT DOCTOR TESTS (Module 42)
# ════════════════════════════════════════════════════════════════════════════

SAMPLE_SCREENPLAY = """INT. CRUMBLING CINEMA - NIGHT

MARCO stands alone in the empty theatre. A single projector beam cuts the darkness. He trembles with fear.

MARCO
(whispering)
This is where it all ends.

He presses PLAY. A secret betrayed on screen. The revelation stuns him.

EXT. ROMAN STREETS - DAY

A younger MARCO chases pigeons with his camera. Joy on his face. Hope for the future. Together with friends, they laugh.

INT. STUDIO - NIGHT

THE PRODUCER confronts MARCO. Fury erupts. He slams the table. Explosion of anger.

PRODUCER
You've ruined everything. You're fired. Career over.

EXT. HARBOR - DAWN

MARCO looks out at the sunrise over the water. New beginnings. Love rekindled.

MARCO
Maybe I was wrong all along.
"""

def test_script_doctor_scene_split():
    from app.script_doctor import ScriptDoctor
    doctor = ScriptDoctor()
    scenes = doctor._split_scenes(SAMPLE_SCREENPLAY)
    assert len(scenes) >= 2


def test_script_doctor_pacing_analysis():
    from app.script_doctor import ScriptDoctor
    doctor = ScriptDoctor()
    scenes = doctor._split_scenes(SAMPLE_SCREENPLAY)
    pacing = doctor._analyse_pacing(scenes)
    assert "average_scene_length_words" in pacing
    assert "pacing_verdict" in pacing
    assert isinstance(pacing["average_scene_length_words"], int)


def test_script_doctor_dialogue_analysis():
    from app.script_doctor import ScriptDoctor
    doctor = ScriptDoctor()
    result = doctor._analyse_dialogue(SAMPLE_SCREENPLAY)
    assert "dialogue_word_ratio" in result
    assert "verdict" in result
    assert 0 <= result["dialogue_word_ratio"] <= 1.0


def test_script_doctor_stakes():
    from app.script_doctor import ScriptDoctor
    doctor = ScriptDoctor()
    result = doctor._assess_stakes(SAMPLE_SCREENPLAY)
    assert result["stake_count"] >= 1  # at least one stake type in sample
    assert "verdict" in result
    assert "detected_stake_types" in result


def test_script_doctor_theme_check():
    from app.script_doctor import ScriptDoctor
    from app.agent_coordinator import get_or_create_memory, clear_memory
    doctor = ScriptDoctor()
    pid = "doctor_test_001"
    clear_memory(pid)
    mem = get_or_create_memory(pid, project_title="The Cinema")
    mem.themes = ["fear", "love", "betrayal"]
    result = doctor._check_themes(SAMPLE_SCREENPLAY, mem)
    assert "project_themes" in result
    assert len(result["themes_found_in_script"]) >= 1
    clear_memory(pid)


def test_script_doctor_scoring():
    from app.script_doctor import ScriptDoctor
    doctor = ScriptDoctor()
    scenes = doctor._split_scenes(SAMPLE_SCREENPLAY)
    act_diag = doctor._diagnose_acts(scenes, len(scenes))
    pacing = doctor._analyse_pacing(scenes)
    stakes = doctor._assess_stakes(SAMPLE_SCREENPLAY)
    score = doctor._score(act_diag, pacing, stakes)
    assert "score" in score
    assert 0 <= score["score"] <= 100
    assert score["grade"] in ("A", "B", "C", "D", "F")


def test_script_doctor_runtime_estimate():
    from app.script_doctor import ScriptDoctor
    doctor = ScriptDoctor()
    runtime = doctor._estimate_runtime(SAMPLE_SCREENPLAY)
    assert runtime >= 0  # any positive estimate is valid


@pytest.mark.asyncio
async def test_script_doctor_full_analysis():
    from app.script_doctor import ScriptDoctor
    doctor = ScriptDoctor()
    result = await doctor.analyse(SAMPLE_SCREENPLAY)
    assert "total_scenes" in result
    assert "pacing" in result
    assert "stakes" in result
    assert "overall_score" in result
    assert "citations" in result
    assert isinstance(result["citations"], list)


@pytest.mark.asyncio
async def test_script_doctor_api_endpoint(client):
    resp = await client.post("/api/script-doctor/analyse", json={
        "screenplay_text": SAMPLE_SCREENPLAY,
        "project_id": None
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert data["total_scenes"] >= 2


# ════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE TESTS (Module 44 & 45)
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_in_memory_cache_basic():
    from app.middleware import InMemoryCache
    cache = InMemoryCache()
    cache.set("key1", {"data": "value"}, ttl_seconds=60)
    result = cache.get("key1")
    assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_in_memory_cache_expiry():
    import time as time_mod
    from app.middleware import InMemoryCache
    cache = InMemoryCache()
    cache.set("expiring_key", "soon gone", ttl_seconds=0)
    time_mod.sleep(0.01)
    result = cache.get("expiring_key")
    assert result is None  # expired


@pytest.mark.asyncio
async def test_in_memory_cache_clear_prefix():
    from app.middleware import InMemoryCache
    cache = InMemoryCache()
    cache.set("project:abc:detail", {"id": "abc"}, 60)
    cache.set("project:abc:scenes", ["s1"], 60)
    cache.set("shot:xyz:frame", "frame_data", 60)
    cache.clear_prefix("project:abc")
    assert cache.get("project:abc:detail") is None
    assert cache.get("project:abc:scenes") is None
    assert cache.get("shot:xyz:frame") == "frame_data"  # unaffected


@pytest.mark.asyncio
async def test_cache_manager_set_get():
    from app.middleware import CacheManager
    mgr = CacheManager()
    await mgr.set("test:manager:key", {"hello": "world"}, ttl=60)
    result = await mgr.get("test:manager:key")
    assert result == {"hello": "world"}


@pytest.mark.asyncio
async def test_retry_decorator_succeeds_on_third_attempt():
    from app.middleware import retry_async
    call_count = {"n": 0}

    @retry_async(max_attempts=3, delay=0.01)
    async def flaky_function():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ConnectionError("Not ready yet")
        return "success"

    result = await flaky_function()
    assert result == "success"
    assert call_count["n"] == 3


@pytest.mark.asyncio
async def test_retry_decorator_raises_after_max():
    from app.middleware import retry_async
    @retry_async(max_attempts=2, delay=0.01)
    async def always_fails():
        raise RuntimeError("Always fails")

    with pytest.raises(RuntimeError, match="Always fails"):
        await always_fails()


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "service" in data


@pytest.mark.asyncio
async def test_cache_health_endpoint(client):
    resp = await client.get("/api/health/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "cache" in data


@pytest.mark.asyncio
async def test_full_health_endpoint(client):
    resp = await client.get("/api/health/full")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]


# ════════════════════════════════════════════════════════════════════════════
# PARSER TESTS (existing, preserved)
# ════════════════════════════════════════════════════════════════════════════

def test_parser_basic():
    from app.parser import parse_screenplay
    text = """INT. OFFICE - DAY

JOHN enters. He looks nervous.

JOHN
We need to talk.

EXT. STREET - NIGHT

MARIA runs down the alley.

MARIA
Stop! Wait for me!"""

    result = parse_screenplay(text)
    assert len(result["scenes"]) == 2
    assert result["scenes"][0]["heading"] == "INT. OFFICE - DAY"
    assert "JOHN" in result["characters"]
    assert "MARIA" in result["characters"]


def test_parser_action_blocks():
    from app.parser import parse_screenplay
    text = """INT. LAB - DAY

DR CHEN studies the sample under a microscope.

DR CHEN
The results are inconclusive.

She writes in her notebook."""

    result = parse_screenplay(text)
    scene = result["scenes"][0]
    actions = [e for e in scene["elements"] if e["type"] == "action"]
    dialogues = [e for e in scene["elements"] if e["type"] == "dialogue"]
    assert len(actions) >= 1
    assert len(dialogues) >= 1
    assert dialogues[0]["character"] == "DR CHEN"
