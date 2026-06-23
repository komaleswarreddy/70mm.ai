import pytest
from app.character_consistency.character_consistency import CharacterConsistencyOrchestrator
from app.director.director_mode import DirectorModePro
from app.director.reference_engine import ReferenceEngine
from app.rag.rag_engine import CinematicRAGEngine
from app.multimodal.multimodal_input import MultimodalInputEngine

def test_character_consistency_orchestrator():
    orchestrator = CharacterConsistencyOrchestrator()
    config = orchestrator.compile_consistency_params(
        reference_image_url="http://localhost:8000/static/test_face.png",
        face_lock=True,
        hair_lock=True,
        costume_lock=True,
        strength=0.75
    )
    assert config["overall_strength"] == 0.75
    assert config["locks"]["face"] is True
    assert config["locks"]["hair"] is True
    assert "instantid" in config
    assert "ipadapter" in config

def test_director_mode_pro_styles():
    director_pro = DirectorModePro()
    
    # Test Nolan Style
    nolan_style = director_pro.get_style_guidance("Nolan")
    assert "imax" in nolan_style["lens"].lower()
    assert "center" in nolan_style["composition"].lower()
    
    # Test Villeneuve Style
    villeneuve_style = director_pro.get_style_guidance("Villeneuve")
    assert "brutalist" in villeneuve_style["composition"].lower()
    assert "overcast" in villeneuve_style["lighting"].lower()

def test_reference_engine_stills():
    ref_engine = ReferenceEngine()
    stills = ref_engine.get_stills_by_director("Villeneuve")
    assert len(stills) > 0
    assert stills[0]["movie"] == "Dune"

@pytest.mark.anyio
async def test_cinematic_rag_vector_search():
    rag = CinematicRAGEngine()
    response = await rag.answer_screenplay_query("Save The Cat Catalyst beat sheet")
    assert response["query"] == "Save The Cat Catalyst beat sheet"
    assert len(response["results"]) > 0
    assert "Blake Snyder" in response["results"][0]["author"]

@pytest.mark.anyio
async def test_multimodal_input_routing():
    engine = MultimodalInputEngine()
    
    # Test Voice script transcription
    voice_res = await engine.process_multimodal_asset("voice", "/static/audio/test_memo.wav")
    assert voice_res["type"] == "voice"
    assert "INT. BRIEFING ROOM" in voice_res["content"]

    # Test Moodboard palette extraction
    mood_res = await engine.process_multimodal_asset("moodboard", "/static/images/moodboard.jpg")
    assert mood_res["type"] == "moodboard"
    assert len(mood_res["palette"]) > 0
