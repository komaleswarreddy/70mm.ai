from app.parser import parse_screenplay

def test_parse_screenplay():
    fountain_script = """
TITLE: MY AMAZING FILM
AUTHOR: GUEST WRITER

.FORCED SCENE HEADING

This is an action line.

JOHN ^
(weary)
It's too early for this.

MARY
(excited)
But the day has begun!
(laughs)

> CUT TO BLACK.

INT. KITCHEN - DAY

The teapot whistles. JOHN stands over the stove.
"""
    
    result = parse_screenplay(fountain_script)
    assert len(result["scenes"]) == 2
    assert result["scenes"][0]["heading"] == "FORCED SCENE HEADING"
    
    elements = result["scenes"][0]["elements"]
    assert elements[0]["type"] == "action"
    
    # Check dual dialogue
    assert elements[1]["type"] == "dialogue"
    assert elements[1]["character"] == "JOHN"
    assert elements[1]["dual"] is True
    
    # Check dialogue parts (parentheticals vs text)
    dialogue_parts_john = elements[1]["dialogue_parts"]
    assert len(dialogue_parts_john) == 2
    assert dialogue_parts_john[0]["type"] == "parenthetical"
    assert dialogue_parts_john[0]["content"] == "(weary)"
    assert dialogue_parts_john[1]["type"] == "dialogue_text"
    assert dialogue_parts_john[1]["content"] == "It's too early for this."
    
    # Check MARY dialogue with multiple parts
    assert elements[2]["type"] == "dialogue"
    assert elements[2]["character"] == "MARY"
    dialogue_parts_mary = elements[2]["dialogue_parts"]
    assert len(dialogue_parts_mary) == 3
    assert dialogue_parts_mary[0]["type"] == "parenthetical"
    assert dialogue_parts_mary[1]["type"] == "dialogue_text"
    assert dialogue_parts_mary[2]["type"] == "parenthetical"
    
    # Check transition
    assert elements[3]["type"] == "transition"
    assert elements[3]["content"] == "CUT TO BLACK."
    
    assert "JOHN" in result["characters"]
    assert "MARY" in result["characters"]
