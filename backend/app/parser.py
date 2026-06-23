import re
from typing import List, Dict, Any

def parse_screenplay(content: str) -> Dict[str, Any]:
    """
    Parses a screenplay in .txt or .fountain format.
    Extracts scene headings, characters, dialogues, action blocks, and transitions.
    """
    # Normalize newlines
    content = content.replace("\r\n", "\n")
    # Split into blocks by one or more blank lines
    blocks = re.split(r'\n\s*\n', content)
    
    scenes = []
    characters = set()
    
    current_scene = None
    scene_counter = 0
    
    def get_or_create_scene(heading: str = "PROLOGUE") -> Dict[str, Any]:
        nonlocal current_scene, scene_counter
        # If we have no scene yet, or if it's a real scene heading, start a new scene
        if current_scene is None or heading != "PROLOGUE":
            scene_counter += 1
            current_scene = {
                "scene_number": scene_counter,
                "heading": heading,
                "elements": []
            }
            scenes.append(current_scene)
        return current_scene

    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
            
        # Skip metadata blocks at the very beginning of the script
        if scene_counter == 0 and current_scene is None:
            is_metadata = False
            for line in lines:
                if re.match(r'^(title|author|authors|source|draft\s*date|contact|credit|credits|genre)\s*:', line, re.IGNORECASE):
                    is_metadata = True
                    break
            if is_metadata:
                continue

        first_line = lines[0]
        
        # 1. Check Scene Heading
        # Fountain headings start with INT., EXT., EST., I/E, or a period '.'
        is_scene_heading = False
        heading_text = ""
        
        if first_line.startswith('.'):
            is_scene_heading = True
            heading_text = first_line[1:].strip().upper()
        else:
            upper_line = first_line.upper()
            prefixes = ("INT.", "EXT.", "INT/EXT", "INT./EXT.", "EXT/INT", "EST.", "INT ", "EXT ", "I/E ")
            if upper_line.startswith(prefixes):
                is_scene_heading = True
                heading_text = upper_line
                
        if is_scene_heading:
            get_or_create_scene(heading_text)
            # If there are subsequent lines in this block, treat them as action lines
            if len(lines) > 1:
                scene = get_or_create_scene()
                scene["elements"].append({
                    "type": "action",
                    "content": "\n".join(lines[1:])
                })
            continue

        # 2. Check Transition
        # Fountain transitions are uppercase ending with TO:, or forced with a leading '>'
        is_transition = False
        transition_text = ""
        if first_line.startswith('>'):
            is_transition = True
            transition_text = first_line[1:].strip().upper()
        else:
            upper_line = first_line.upper()
            if upper_line.isupper() and (upper_line.endswith("TO:") or upper_line.startswith("FADE ")):
                is_transition = True
                transition_text = upper_line
                
        if is_transition:
            scene = get_or_create_scene()
            scene["elements"].append({
                "type": "transition",
                "content": transition_text
            })
            # Handle subsequent lines in transition block as action
            if len(lines) > 1:
                scene["elements"].append({
                    "type": "action",
                    "content": "\n".join(lines[1:])
                })
            continue

        # 3. Check Character + Dialogue
        # Character names are uppercase, not a scene heading/transition, and have subsequent lines.
        is_character = False
        clean_char_name = ""
        is_dual = False
        
        # Match character name, optional parenthetical (O.S., V.O., etc.), and optional dual-dialogue "^"
        char_match = re.match(r'^([A-Z0-9\s\-\#\.\&]+)(?:\s*\(.*\))?(\s*\^)?$', first_line)
        if char_match:
            candidate_name = char_match.group(1).strip()
            # Check if it has alphabetic characters and is uppercase
            if candidate_name and any(c.isalpha() for c in candidate_name) and candidate_name.isupper():
                # Make sure it's not a scene heading prefix or transition
                if not candidate_name.startswith(("INT", "EXT", "I/E")) and not candidate_name.endswith("TO:"):
                    is_character = True
                    clean_char_name = candidate_name
                    if char_match.group(2):
                        is_dual = True

        if is_character and len(lines) > 1:
            dialogue_lines = lines[1:]
            dialogue_elements = []
            
            # Sub-parse parentheticals inside the dialogue block
            current_dialogue = []
            for line in dialogue_lines:
                if line.startswith('(') and line.endswith(')'):
                    # If we had dialogue before this parenthetical, flush it
                    if current_dialogue:
                        dialogue_elements.append({
                            "type": "dialogue_text",
                            "content": " ".join(current_dialogue)
                        })
                        current_dialogue = []
                    dialogue_elements.append({
                        "type": "parenthetical",
                        "content": line
                    })
                else:
                    current_dialogue.append(line)
            
            if current_dialogue:
                dialogue_elements.append({
                    "type": "dialogue_text",
                    "content": " ".join(current_dialogue)
                })

            characters.add(clean_char_name)
            scene = get_or_create_scene()
            
            # Combine back to string for backwards compatibility database save
            full_dialogue_content = "\n".join(lines[1:])
            
            scene["elements"].append({
                "type": "dialogue",
                "character": clean_char_name,
                "content": full_dialogue_content,
                "dual": is_dual,
                "dialogue_parts": dialogue_elements
            })
            continue

        # 4. Fallback: Action Block
        scene = get_or_create_scene()
        scene["elements"].append({
            "type": "action",
            "content": block
        })
        
    return {
        "scenes": scenes,
        "characters": sorted(list(characters))
    }
