from app.shot_prompt_builder import build_shot_prompt, NEGATIVE_PROMPT_BASE


def test_build_shot_prompt_includes_core_cinematography():
    shot = {"shot_size": "Close-Up", "camera_angle": "Low", "lens_mm": 85, "movement": "Static"}
    scene = {"heading": "INT. ROOM - DAY", "visual_emphasis": "His trembling hands."}
    result = build_shot_prompt(shot, scene)
    assert "Close-Up" in result["positive_prompt"]
    assert "Low angle" in result["positive_prompt"]
    assert "85mm lens" in result["positive_prompt"]
    assert "trembling hands" in result["positive_prompt"]
    assert result["negative_prompt"] == NEGATIVE_PROMPT_BASE


def test_build_shot_prompt_is_photoreal_not_illustration():
    """Regression test for the confirmed root cause of shots rendering as
    painterly/illustrated art instead of photorealistic cinema."""
    result = build_shot_prompt({"shot_size": "Wide", "camera_angle": "Eye Level"}, {})
    lowered = result["positive_prompt"].lower()
    assert "illustration" not in lowered
    assert "photorealistic" in lowered
    for term in ("illustration", "painting", "cartoon", "anime", "digital art"):
        assert term in result["negative_prompt"].lower()


def test_build_shot_prompt_includes_action_from_reasoning_and_notes():
    """Regression test for the confirmed cause of two same-scene shots with
    different intended action producing a byte-identical prompt."""
    shot_a = {
        "shot_size": "Medium Shot", "camera_angle": "Eye Level",
        "reasoning": "John slams his fist on the table, shouting that he knows about the affair.",
        "notes": "Actor leans forward aggressively.",
    }
    shot_b = {
        "shot_size": "Medium Shot", "camera_angle": "Eye Level",
        "reasoning": "Mary reaches across the table to take John's hand, quietly asking for forgiveness.",
        "notes": "Actor softens posture, slow blink.",
    }
    result_a = build_shot_prompt(shot_a, {})
    result_b = build_shot_prompt(shot_b, {})
    assert result_a["positive_prompt"] != result_b["positive_prompt"]
    assert "slams his fist" in result_a["positive_prompt"]
    assert "reaches across the table" in result_b["positive_prompt"]


def test_build_shot_prompt_has_no_negated_reference_instruction():
    """The composition pass gets no reference images, and Flux's T5 encoder
    does not reliably honour negation, so "do not copy their pose, clothing,
    framing" only injected those concepts. It must stay out of the prompt."""
    characters = [{"name": "Vasanth", "description": "A young man, warm smile."}]
    with_chars = build_shot_prompt({"shot_size": "Wide", "camera_angle": "Eye Level"}, {}, characters)
    assert "do not copy" not in with_chars["positive_prompt"]


def test_build_shot_prompt_includes_scene_wardrobe_and_period():
    characters = [{"name": "RAM", "description": "A 28-year-old army lieutenant.",
                   "wardrobe": "a cream cotton half-sleeve shirt and grey trousers"}]
    p = build_shot_prompt({"shot_size": "Medium Shot"}, {"heading": "INT. TRAIN - DAY", "period": "India, 1965"},
                          characters)["positive_prompt"]
    assert "RAM: A 28-year-old army lieutenant. Wearing a cream cotton half-sleeve shirt" in p
    assert "set in India, 1965" in p


def test_build_shot_prompt_omits_movement_when_static():
    shot = {"shot_size": "Wide", "camera_angle": "Eye Level", "movement": "Static"}
    result = build_shot_prompt(shot, {})
    assert "camera movement" not in result["positive_prompt"]

def test_build_shot_prompt_includes_movement_when_not_static():
    shot = {"shot_size": "Wide", "camera_angle": "Eye Level", "movement": "Dolly"}
    result = build_shot_prompt(shot, {})
    assert "Dolly camera movement" in result["positive_prompt"]

def test_build_shot_prompt_includes_locked_character_descriptions():
    shot = {"shot_size": "Two-Shot", "camera_angle": "Eye Level"}
    characters = [{"name": "Vasanth", "description": "A young man, warm smile."}]
    result = build_shot_prompt(shot, {}, characters)
    assert "Vasanth: A young man, warm smile." in result["positive_prompt"]

def test_build_shot_prompt_includes_lighting_detail():
    shot = {"shot_size": "Medium", "camera_angle": "Eye Level",
             "lighting_detail": {"quality": "Hard", "direction": "side", "color_temp_k": 3200}}
    result = build_shot_prompt(shot, {})
    assert "hard key light from the side" in result["positive_prompt"].lower()
    assert "3200K" in result["positive_prompt"]

def test_build_shot_prompt_is_deterministic_not_llm():
    # Same input -> byte-identical output, twice in a row (no randomness/LLM call).
    shot = {"shot_size": "Wide", "camera_angle": "Eye Level"}
    assert build_shot_prompt(shot, {}) == build_shot_prompt(shot, {})

def test_build_shot_prompt_handles_missing_fields_gracefully():
    result = build_shot_prompt({}, {})
    assert result["positive_prompt"]  # never empty, has sane defaults
    assert "Medium Shot" in result["positive_prompt"]

def test_build_shot_prompt_filters_out_fallback_status_text():
    """Stage 4/5's deterministic fallback writes status text like 'Auto-
    generated fallback composition (AI cinematography unavailable).' into
    composition_notes/framing — that must never leak into the actual image
    prompt as if it were descriptive content."""
    shot = {
        "shot_size": "Wide", "camera_angle": "Eye Level",
        "framing": "Standard framing.",
        "composition_notes": "Auto-generated fallback composition (AI cinematography unavailable).",
    }
    result = build_shot_prompt(shot, {})
    assert "unavailable" not in result["positive_prompt"].lower()
    assert "fallback" not in result["positive_prompt"].lower()


def test_build_shot_prompt_states_multiple_people_share_the_frame():
    """Regression: a two-shot rendered only one character because the prompt
    listed each as a separate attribute phrase rather than saying two people
    are in frame together."""
    characters = [
        {"name": "RAM", "description": "A 28-year-old army lieutenant."},
        {"name": "SITA", "description": "A 27-year-old Telugu woman."},
    ]
    result = build_shot_prompt({"shot_size": "Two-Shot", "camera_angle": "Eye Level"}, {}, characters)
    p = result["positive_prompt"]
    assert "2 people together in the same frame" in p
    assert "RAM" in p and "SITA" in p

def test_build_shot_prompt_single_character_keeps_simple_form():
    characters = [{"name": "RAM", "description": "A 28-year-old army lieutenant."}]
    p = build_shot_prompt({"shot_size": "Close-Up", "camera_angle": "Eye Level"}, {}, characters)["positive_prompt"]
    assert "people together in the same frame" not in p
    assert "RAM: A 28-year-old army lieutenant." in p


def test_negative_prompt_covers_wardrobe_and_limb_defects():
    """Regression: live output produced a duplicated forearm, twisted wrists
    and a shirtless character. The generic 'extra limbs / mutated hands'
    terms alone did not prevent it."""
    neg = NEGATIVE_PROMPT_BASE.lower()
    for term in ("shirtless", "bare chest", "extra arms", "duplicated limbs",
                 "twisted wrist", "fused fingers", "malformed hands"):
        assert term in neg, term


def test_scene_emphasis_is_only_a_fallback_for_shots_without_their_own_staging():
    scene = {"heading": "EXT. OUTPOST - DAY", "visual_emphasis": "focus on the plain envelope"}
    staged = build_shot_prompt({"shot_size": "Wide Shot", "framing": "gate centre, mountains left"}, scene)
    unstaged = build_shot_prompt({"shot_size": "Wide Shot"}, scene)
    assert "plain envelope" not in staged["positive_prompt"]
    assert "plain envelope" in unstaged["positive_prompt"]


def test_placeholder_practicals_are_not_written_into_the_prompt():
    shot = {"shot_size": "Medium Shot", "lighting_detail": {"quality": "soft", "direction": "left", "practicals": "None"}}
    assert "practical lighting" not in build_shot_prompt(shot, {})["positive_prompt"]
    shot["lighting_detail"]["practicals"] = "kerosene lantern"
    assert "practical lighting: kerosene lantern" in build_shot_prompt(shot, {})["positive_prompt"]


def test_wide_shots_state_that_people_are_small_in_frame():
    wide = build_shot_prompt({"shot_size": "Wide Shot"}, {}, [{"name": "RAM", "description": "A lieutenant."}])
    close = build_shot_prompt({"shot_size": "Close-Up"}, {}, [{"name": "RAM", "description": "A lieutenant."}])
    assert "small full-length figures" in wide["positive_prompt"]
    assert "small full-length figures" not in close["positive_prompt"]
