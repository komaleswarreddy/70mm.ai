# MASTER BUILD PROMPT — 70MM.ai Group 3: Storyboard & Cinematography Engine (End-to-End)

> Copy everything below the line into your coding agent (Claude Code, etc.) pointed at the `70MM.ai` repo. It is written to be handed to an engineer/agent directly — it assumes the existing stack in `implementation_plan.md` and extends it, it does not replace it.

---

## 0. Role & ground rules

You are a senior AI-filmmaking systems engineer building the **Storyboard & Cinematography Engine** (Group 3) for the 70MM.ai project. You are extending an existing FastAPI + Next.js codebase — do not propose a rewrite or a different stack. Confirmed existing stack you must build on:

- Backend: FastAPI (Python 3.11), SQLite + SQLAlchemy async ORM
- AI text/reasoning: Gemini 2.5 Flash (REST/SDK)
- Image generation: ComfyUI running Flux.1-dev, with Pillow-based local fallback
- Frontend: Next.js 14 + TypeScript + Tailwind + Shadcn/Radix
- Existing backend files to extend, not replace: `parser.py`, `ai_service.py`, `comfy_client.py`, `image_service.py`, `export_service.py`, `models.py`, `schemas.py`, `routes/`

Hard constraints:
1. Every new tool/model/library must be **free and either self-hostable or free-tier-usable at production volume** (no per-image SaaS billing).
2. **License safety**: do not ship InsightFace's pretrained face-embedding weights or IP-Adapter-FaceID/InstantID's face checkpoints in a commercial code path — they are research/non-commercial licensed. Use PhotoMaker V2 and/or UNO/UMO for character identity instead; they carry no such restriction.
3. Never fabricate a real, identifiable public figure's likeness in a generated character. Character references must be original/synthetic or user-supplied consented images only.
4. Everything must run end-to-end without a human manually clicking through a GUI tool mid-pipeline — this is an automated pipeline, not an artist workflow.

---

## 1. Objective

Input: a 120–130 page screenplay (plain text or Fountain/.fdx format).
Output: a complete set of numbered storyboard board sheets — visually and structurally matching the attached reference layout (grid of numbered panels grouped ~5 scenes per board, each panel showing shot size / lens / camera movement underneath, a board header with title/length/page range, a board footer legend showing camera style / color tone / lighting / mood / notes / lens guide) — plus a machine-readable shot list export (CSV/PDF).

Definition of done: feed in a full screenplay → get back N board-sheet images (PNG/PDF) that a human 1st AD or DP could hand to a crew, without manual per-shot editing required (manual *refinement* via the editor endpoints is fine and expected).

---

## 2. Pipeline (build in this exact order — each stage is a working, testable milestone before the next starts)

```
SCREENPLAY (text / Fountain / FDX)
   → STAGE 1: Deterministic parse (scenes, sluglines, characters, dialogue, action)
   → STAGE 2: Hierarchical structuring (Acts → Sequences → Beats) via LLM
   → STAGE 3: Scene understanding (emotion, conflict, objects, visual emphasis, continuity flags)
   → STAGE 4: Automatic shot division (rules + LLM reasoning, with justification per shot)
   → STAGE 5: Cinematography plan per shot (camera/lens/angle/movement/lighting/mood/palette)
   → STAGE 6: Character asset system (reference bank, identity locking)
   → STAGE 7: Image generation (ComfyUI + Flux.1-dev + PhotoMaker V2 / UNO + ControlNet)
   → STAGE 8: Board compositor (exact reference layout, grid + header + footer legend)
   → STAGE 9: Visual continuity QA (flag drift, trigger regeneration)
   → STAGE 10: Shot list export (CSV/PDF) + natural-language shot editor API
```

### Stage 1 — Deterministic screenplay parsing
- Use the MIT-licensed `screenplay-tools` parser (or an equivalent Fountain-format grammar you implement) to split the raw script into typed elements: scene heading (INT/EXT, location, time-of-day), action lines, character cues, dialogue, parentheticals, transitions.
- Do **not** let the LLM do this step — deterministic parsing must produce the ground-truth scene boundaries and character name list first. The LLM only reasons on top of this structure.
- Output: `scenes: [{scene_number, heading, location, time_of_day, raw_action, raw_dialogue[], characters_present[]}]`.
- Extend `parser.py` with this and unit-test it against at least 3 real screenplay samples (varying formatting quality) before moving on.

### Stage 2 — Hierarchical structuring (Acts/Sequences/Beats)
- Feed Stage 1's scene list to Gemini 2.5 Flash in batches (never the whole 130 pages in one call — chunk by act-sized windows, e.g. 25–35 scenes at a time, with the prior act's summary carried forward as context so the LLM keeps global continuity).
- Require **strict JSON output** with a schema like:
```json
{
  "acts": [{
    "act_number": 1,
    "title": "string",
    "sequences": [{
      "sequence_title": "string",
      "scene_numbers": [1,2,3],
      "beats": [{"beat_title": "string", "scene_numbers": [1,2], "beat_purpose": "string"}]
    }]
  }]
}
```
- Validate the JSON against the schema; on failure, re-prompt with the validation error appended (repair loop, max 2 retries) rather than silently accepting malformed output.
- Extend `ai_service.py` with this as its own function, separate from Stage 3/4/5 calls — don't conflate structuring with per-scene detail extraction.

### Stage 3 — Scene understanding
- For each scene (batched, e.g. 5–10 scenes per LLM call), extract: characters present, location, time, primary action, dominant emotion, conflict (if any), important objects/props, key dialogue lines, "visual emphasis" (what the camera should care about), and continuity requirements (props/costume/state that must carry from a previous scene).
- Output schema per scene:
```json
{
  "scene_number": 1,
  "characters": ["Rukhmika", "Vasanth"],
  "location": "Plant Nursery",
  "time": "Day",
  "action_summary": "string",
  "emotion": "excited | nostalgic | tense | ...",
  "conflict": "string|null",
  "key_objects": ["motorbike", "plants"],
  "visual_emphasis": "string",
  "continuity_notes": ["Vasanth wears same jacket as scene 4"]
}
```

### Stage 4 — Automatic shot division
- Build a rules-first, LLM-refined shot planner. Rules give a strong prior; the LLM adjusts and justifies:
  - Establishing/arrival scenes → 1 wide establishing shot + 1–2 medium shots.
  - Phone-call scenes → intercut CU on each speaker + 1 insert (phone screen/hands) + optional two-shot split-frame.
  - Friends-arrive / group scenes → wide/two-shot + medium two-shot + reaction close-ups.
  - Action/movement (bus stop, road, motorbike) → wide + medium + tracking/insert shots of vehicle/props.
  - Emotional beats → push toward CU/ECU; conflict beats → OTS + two-shot.
- Each shot object must carry: `shot_type` (one of: Wide Establishing, Wide, Medium, Medium Close-Up, Close-Up, Extreme Close-Up, Two-Shot, Over-the-Shoulder, POV, Insert, Cutaway), and a `reasoning` string (why this shot exists — required, not optional, this is explicitly called out in the spec).
- Extend `models.py` with a `Shot` table (if not already sufficient) carrying `scene_id`, `shot_number`, `shot_type`, `reasoning`, `order_in_scene`.

### Stage 5 — Cinematography plan
- For every shot from Stage 4, generate a full cinematography record:
```json
{
  "shot_size": "Wide Shot",
  "camera_angle": "Eye Level | Low | High | Dutch",
  "lens_mm": 35,
  "camera_height": "string",
  "movement": "Static | Pan | Tilt | Dolly | Handheld | Push-In",
  "framing": "string",
  "composition_notes": "string",
  "lighting": {
    "key": "string", "fill": "string", "backlight": "string",
    "practicals": "string", "quality": "Hard | Soft",
    "direction": "string", "intensity": "string", "color_temp_k": 5600
  },
  "mood": "string",
  "color_palette": "string",
  "contrast": "Low | Medium | High",
  "depth_of_field": "Shallow | Deep",
  "perspective_notes": "string"
}
```
- Derive lens/angle defaults from shot_type (e.g. Wide→24–35mm, CU→50–85mm, establishing→24mm) but let the LLM override based on scene mood/emotion from Stage 3. This is what populates the "Lens / Movement" line under each panel in the final board image.
- New table: `ShotCinematography` (1:1 with `Shot`).

### Stage 6 — Character asset & consistency system
- For every named character, build a **character bible** record: canonical description, 1–4 locked reference images (either user-uploaded or generated once with a fixed seed and then frozen), and a stored identity embedding.
- New table: `CharacterAsset(character_id, name, description, reference_image_paths[], embedding_vector, locked_seed)`.
- Generation rule: **never generate a character's first appearance without first creating and locking their reference set.** Every subsequent shot containing that character must condition on the locked references.
- Use **PhotoMaker V2** for single-character shots (zero-shot from the reference images, no per-character training needed) and **UNO/UMO** for shots with 2+ named characters together (they correctly place multiple identities in one frame). Reserve per-character LoRA/DreamBooth training only as a fallback for hero characters if PhotoMaker/UNO fidelity isn't sufficient after testing.

### Stage 7 — Image generation (ComfyUI)
- Extend `comfy_client.py` to build and queue a ComfyUI workflow JSON per shot, using Flux.1-dev as the base checkpoint, with:
  - The relevant character reference image(s)/embeddings injected via the PhotoMaker V2 or UNO custom node depending on character count in the shot.
  - ControlNet (depth or pose) optionally injected when the cinematography plan specifies a precise camera angle/blocking that pure prompting won't reliably hit.
  - A prompt built deterministically from the Stage 5 cinematography JSON (shot size, angle, lens, lighting, mood, palette) plus the Stage 3 scene description plus each present character's locked description — build this as a template function, not free-text LLM prose, so results stay controllable and debuggable.
- Queue via the ComfyUI `/prompt` API, poll for completion, store the output image path against the `Shot` row, and implement retry-on-failure (max 2 retries) before falling back to the existing Pillow placeholder.

### Stage 8 — Board compositor (must visually match the reference layout)
- This is a pure image-compositing step — do not expect ComfyUI or any generation model to produce the finished multi-panel board. Build it with Pillow (or an HTML/CSS template rendered headless to PNG) in a new `board_service.py`:
  - Group shots into boards of ~5 scenes each (mirroring "Board 1: Scenes 1–5" in the reference).
  - Board header row: project title, board number, scene range title, screenplay-portion length, page range.
  - Per-scene row: scene heading strip (e.g. "SCENE 1: EXT. PLANT NURSERY – DAY"), then a grid of numbered panels ("1.1", "1.2", ...) for that scene's shots.
  - Under each panel image: shot type label, lens/mm, camera movement — pulled straight from the Stage 5 cinematography record.
  - Board footer legend bar: camera style, color tone, lighting approach, mood, general notes, and a lens-guide chart (wide/normal/close-up mm reference) — generate this from aggregate/default project settings, editable per project.
  - Output one merged PNG (and a print-ready PDF via the existing `reportlab` dependency) per board.

### Stage 9 — Visual continuity QA
- After each shot image is generated, run it through a continuity-check service:
  - Face embedding comparison (via a **commercially-licensed** face-embedding model, or DeepFace with a commercially-usable backbone — verify license before shipping) between this shot and the character's locked reference set → flag if similarity drops below a threshold (start at cosine ≥ 0.55, tune empirically).
  - CLIP embedding comparison for costume/style/location drift across shots that should share those elements.
  - OpenCV color-histogram comparison for lighting/color-grade consistency within a scene.
  - Any shot below threshold gets flagged `needs_review` and queued for regeneration with reinforced reference conditioning, not silently accepted.

### Stage 10 — Shot list export + editor API
- Extend `export_service.py` to emit a CSV/PDF shot list with columns: Scene, Shot, Type, Lens, Movement, Lighting, Characters — directly from the `Shot` + `ShotCinematography` tables, no extra data modeling needed.
- Add an editor endpoint (`PATCH /shots/{id}/edit`) that accepts natural-language instructions ("make this a low-angle shot", "change to night", "use a 50mm lens", "move camera behind the character"), uses the LLM to translate that into a structured diff against the `ShotCinematography` record, updates the record, and re-queues Stage 7 generation for just that one shot.

---

## 3. New/updated data model (extend `models.py`)

- `Shot`: scene_id, shot_number, shot_type, reasoning, order_in_scene, needs_review (bool)
- `ShotCinematography`: shot_id (1:1), shot_size, camera_angle, lens_mm, camera_height, movement, framing, composition_notes, lighting (JSON), mood, color_palette, contrast, depth_of_field, perspective_notes
- `CharacterAsset`: character_id, name, description, reference_image_paths (JSON list), embedding_vector, locked_seed
- `Board`: board_number, scene_range_start, scene_range_end, title, output_image_path, output_pdf_path

## 4. New/updated API routes

- `POST /projects/{id}/parse` → Stage 1
- `POST /projects/{id}/structure` → Stage 2
- `POST /scenes/{id}/understand` → Stage 3
- `POST /scenes/{id}/shots/generate-plan` → Stage 4 + 5 combined
- `POST /characters/{id}/lock-reference` → Stage 6
- `POST /shots/{id}/generate-image` → Stage 7
- `POST /projects/{id}/boards/compose` → Stage 8 (build all boards for the project)
- `POST /shots/{id}/continuity-check` → Stage 9
- `PATCH /shots/{id}/edit` → Stage 10 editor
- `GET /projects/{id}/export/shotlist.csv` / `.pdf` → Stage 10 export

## 5. Build order / milestones (do not skip ahead)

1. Stage 1 parser working + unit-tested on 3 real scripts.
2. Stage 2 + 3 structuring producing valid, schema-checked JSON on a full 130-page script.
3. Stage 4 + 5 producing a complete shot list with cinematography data for one full act (no images yet) — get this reviewed before generating a single image.
4. Stage 6 character bible + Stage 7 basic image generation for a single test scene (5–10 shots, 2–3 characters) — validate character consistency manually before scaling.
5. Stage 8 board compositor producing one board that visually matches the reference layout for that same test scene.
6. Run Stage 9 continuity QA against that board's shots, tune thresholds.
7. Only after 1–6 are validated on a test scene: run Stages 1–9 across the full screenplay in a batch job, then Stage 10 export.

## 6. Acceptance criteria

- A real 120–130 page screenplay run end-to-end produces board PNGs/PDFs whose structure matches the reference (numbered grid, per-panel lens/movement labels, board header/footer legend) with no manual per-shot intervention required to get a first pass.
- The same named character generated in an early scene and a late scene scores above the continuity threshold on face-embedding similarity.
- Every shot has a non-empty `reasoning` field explaining why that shot exists.
- Shot list CSV/PDF exports open correctly and match the on-screen shot data.
- No non-commercial-licensed model weights (InsightFace/IP-Adapter-FaceID/InstantID face checkpoints) are present in the shipped generation code path.

## 7. Explicit non-goals for this phase

- Do not attempt video/animatic generation — static storyboard frames only.
- Do not integrate Boords, StudioBinder, FrameForge, or WonderUnit Storyboarder as dependencies — they were evaluated and rejected for lack of API/automation fit (see `STORYBOARD_ENGINE_TOOL_RESEARCH.md` in this repo for the full reasoning).
- Do not call any paid hosted inference API as the production image-generation path — self-hosted ComfyUI is the production engine; hosted APIs are prototyping-only.
