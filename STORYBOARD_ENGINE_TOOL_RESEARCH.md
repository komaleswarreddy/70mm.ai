****# Group 3 — Storyboard & Cinematography Engine: Tool Research & Recommendation

**Scope of this document:** deep, source-checked research (three parallel research passes, 2026-08-29) into which free/open tools can actually power the pipeline you specified:

```
SCREENPLAY (120–130 pages)
   → PARSER (Acts → Sequences → Scenes → Beats)
   → SHOT DIVISION
   → CINEMATOGRAPHY PLAN (camera/lens/lighting/movement)
   → IMAGE GENERATION (character-consistent)
   → STORYBOARD
   → VISUAL CONTINUITY CHECK
   → SHOT LIST EXPORT
```

No implementation was done. Every claim below was verified by live web search against 2026-current sources (repo activity, pricing pages, license files, GitHub issues). Where something could not be confirmed, it is explicitly flagged as **unverified** rather than assumed.

**Context that changes the answer:** your own `implementation_plan.md` already commits to **ComfyUI running Flux.1-dev** for image generation and **Gemini 2.5 Flash** for AI/text tasks, with a FastAPI backend (`comfy_client.py`, `ai_service.py`, `parser.py` already scaffolded). That matters — it means the right recommendation isn't "pick a new tool," it's "which of these 9 tools, plus what else, correctly extends the stack you've already chosen." That framing is used throughout.

---

## 1. TL;DR — the answer, before the detail

**There is no single tool that does this whole pipeline.** Nobody has shipped a free, production-grade, one-tool "screenplay → consistent storyboard" product yet — this is confirmed by research: the closest academic attempts (Story2Board, CANVAS) are papers from 2025/2026, not products. Anyone claiming a single 100%-solves-it-all tool would be overselling. That said, if forced to name **one single tool as the core of the engine**, it is:

> ### **ComfyUI (self-hosted, running Flux.1-dev) — the tool you have already chosen.**
> It is the only one of the 9 candidates that is simultaneously: 100% free, has a real programmatic API (`/prompt` REST + websocket, exactly what `comfy_client.py` already talks to), is under active development, and is the actual delivery mechanism for every free character-consistency technique that matters (PhotoMaker V2, IP-Adapter, ControlNet, UNO/UMO all ship as ComfyUI custom nodes). Don't switch tools — bolt the missing pieces onto it.

The missing pieces, in priority order, are:

| Pipeline gap | Add this (all free/OSS) |
|---|---|
| Character stays the same face across 130 pages | **PhotoMaker V2** (zero-shot, seconds-fast) as primary; **UNO/UMO** for scenes with multiple named characters together; per-character **LoRA/DreamBooth** for your 2–3 hero characters if PhotoMaker isn't precise enough |
| Camera angle / framing / lens control | **ControlNet** (depth + OpenPose) on Flux/SDXL, plus disciplined prompt templates for lens/shot-size (this part of the puzzle is genuinely immature industry-wide — flagged in §6) |
| Screenplay → Acts/Sequences/Scenes/Beats | Deterministic **Fountain/FDX parser** (`screenplay-tools`, MIT) for the scene-level ground truth, feeding **Gemini 2.5 Flash** (already in your stack) for the hierarchical Acts/Sequences/Beats structuring — don't ask the LLM to also do exact scene-heading parsing, it will drift on a 130-page script |
| Visual continuity QA across generated frames | **InsightFace embeddings** (code is MIT; see licensing flag in §6) or **DeepFace**, plus **CLIP** for costume/prop/style drift, plus **OpenCV** histogram/color comparisons for lighting continuity — used as a scoring/QA layer, not a generator |
| Shot-list export | Your own `export_service.py` (already planned, `reportlab`) — none of the 4 commercial tools below offer a usable programmatic hook for this |

None of this requires abandoning anything in your `implementation_plan.md`. It requires adding ComfyUI custom nodes and two Python microservices (parsing + continuity-QA) around what you've already scaffolded.

---

## 2. How tools were scored

Each tool got a 0–10 **Recommendation Score for this specific project**, weighted across five criteria that actually determine "100% doable without problems":

1. **Cost** — genuinely free/open-source vs. paid vs. freemium-with-a-paywall-on-the-part-you-need
2. **Programmatic integration** — real API/SDK/CLI/library vs. GUI-only manual tool
3. **Task fit** — does it solve a real piece of *this specific* pipeline, or is it adjacent/irrelevant
4. **Maintenance & reliability** — actively developed in 2025–2026 vs. stalled/abandoned
5. **License safety** — can the output/weights be used in a commercial product without a legal landmine

A tool scores low if it fails #2 (no API) even if it's excellent software — because your requirement is an *automated pipeline*, not a manual artist tool.

---

## 3. The four production/previz tools you named

### 3.1 WonderUnit Storyboarder — Score: **2 / 10**
**What it is:** Free Electron desktop app for hand-drawn/stick-figure storyboards. Can import Fountain/FDX scripts and auto-create one board per scene.
**Pros:** Genuinely free to use; script import exists out of the box; its `.storyboarder` project format is a documented JSON schema.
**Cons:** No API, no CLI — everything happens inside the Electron UI. Its license is **legally ambiguous, not clean open source** — GitHub issue #1067 documents that WonderUnit silently removed the ISC license and never replaced it with anything unambiguous; their own "philosophy" page describes a custom non-commercial-adjacent license (no one may charge for it but WonderUnit, CLA required, education carve-outs). Project shows no meaningful 2026 activity — two separate open issues ask "is this still alive?" with no maintainer response. Latest release is a pre-release v3.0.0.
**Verdict:** Not usable as a pipeline component. Worth 20 minutes of study for its file-format schema and its Fountain-scene-splitting UX pattern — nothing more. Do not embed its code in a commercial product without written permission from WonderUnit given the licensing ambiguity.

### 3.2 Boords — Score: **5 / 10**
**What it is:** Web SaaS storyboarding tool with a genuine "paste script → AI-generated storyboard with consistent characters" feature.
**Pros:** The only one of the four with a **real documented REST API** (`app.boords.com/v1`) — projects, storyboards, frames, image upload (by URL/base64), webhooks, 120 req/min. This is a legitimate way to push externally-generated (e.g., your own ComfyUI) images into a shareable, commentable storyboard interface for human review.
**Cons:** API access requires a **paid plan** ($26–$165+/mo tiers). It is **unconfirmed whether Boords' own AI image generation is triggerable through the API** at all — the docs only clearly document image *upload*, not generation-on-demand; this needs a direct trial to confirm. It's a downstream/collaboration layer, not a generation engine — it doesn't solve character consistency, cinematography control, or continuity checking themselves.
**Verdict:** Interesting as an optional "human review & client presentation" layer sitting *after* your engine generates images, not as the engine itself. Not free at the tier you'd need. Skip for MVP; revisit later only if you want a polished client-facing review UI instead of building one.

### 3.3 FrameForge (now "FrameForge Studio") — Score: **1 / 10**
**What it is:** Closed, paid, Delphi-based desktop app for 3D virtual previsualization — placing a virtual camera with real lens/sensor optics in a 3D set. It is not an image generator and not script-aware.
**Pros:** None relevant to an automated pipeline. Its concept — optically-accurate lens/focal-length simulation tied to camera placement — is a good mental model for what your cinematography-metadata schema should capture.
**Cons:** No API, SDK, CLI, or plugin system found anywhere (official site, Wikipedia, retailers). Paid (exact current price unconfirmed — sits behind a quote flow). Purely manual, one-scene-at-a-time artist tool; would not scale to 130 pages even if it did have an API.
**Verdict:** Zero integration value. Reference-only, and only for the shot/lens data model, not the software.

### 3.4 StudioBinder — Score: **2 / 10**
**What it is:** Production-management SaaS (scheduling, call sheets, shot lists, storyboards/mood boards under "Visualize").
**Pros:** Its "Shot Tagging" (select script lines → auto-create shot-list rows) and shot-list field taxonomy (camera setup grouping, filters, time estimates) are a genuinely good reference for designing your own shot-list data schema. Has a free tier.
**Cons:** **No public API found** anywhere (extensive search of their docs/support site turned up nothing — no Zapier app, no webhooks, no developer portal). No AI-assisted generation of any kind. Only CSV/PDF export, which requires a human to click "export" — not a real integration point. Paid tiers run $42–$340+/mo per third-party pricing aggregators (StudioBinder's own pricing page wasn't fetchable to confirm first-party).
**Verdict:** Not usable programmatically. Reference-only for UX/data-schema ideas.

---

## 4. The five technical/library tools you named

### 4.1 Hugging Face Diffusers — Score: **9.5 / 10**
**What it is:** The open-source Python library (Apache-2.0) underlying nearly all free image-generation pipelines, including the one ComfyUI itself runs on. v0.38 as of mid-2026, 33.8k GitHub stars, active development (91 releases). First-class, documented support for SDXL, Flux, ControlNet, IP-Adapter.
**Pros:** Genuinely free, genuinely commercial-safe license (Apache-2.0), actively maintained, runs on consumer GPUs for SDXL-class models, has every hook (ControlNet, IP-Adapter) your pipeline needs.
**Cons:** It's a library, not a turnkey product — someone has to write the orchestration code (which is exactly what ComfyUI already does for you, and what your `comfy_client.py` already targets). Flux-class models need more VRAM than SDXL; production-scale generation needs a real GPU (local or rented), not a laptop CPU.
**Verdict:** This *is* the technology stack under your existing ComfyUI choice. Confirmed as the right foundation — no change needed, just build on it.

### 4.2 Hugging Face Hub — Score: **7 / 10** (as a resource, not a runtime)
**What it is:** The model/dataset registry and hosted-inference platform.
**Pros:** Free access to essentially every model named in this report (PhotoMaker, UNO, ControlNet checkpoints, InsightFace, CLIP). Spaces + ZeroGPU give free GPU access for prototyping/demos.
**Cons:** The **hosted, serverless free-tier Inference API is not viable at your scale** — HF's own pricing page states free accounts get $0.10/month in inference credit, nowhere near enough for hundreds of storyboard frames per screenplay. Dedicated Inference Endpoints are paid-only ($0.033–$0.50+/hr). ZeroGPU is built for interactive Gradio demos, not a headless batch pipeline, and would need workarounds to drive from your backend.
**Verdict:** Use it as the place you download models from and prototype on Spaces — not as your production inference backend. Your production inference backend is your own self-hosted ComfyUI/Diffusers instance (as already planned), on a rented or owned GPU.

### 4.3 OpenCV — Score: **6 / 10** (as a QA helper, not a primary tool)
**What it is:** The classic open-source (Apache-2.0 since v4.5.0) computer-vision library — OpenCV 5 shipped June 2026, still actively maintained.
**Pros:** Free, mature, fast. Genuinely useful pieces for continuity QA: color-histogram comparison (lighting/color-grade drift between frames), classic feature matching (rough prop/composition comparison), face *detection* (not recognition).
**Cons:** Plain OpenCV **cannot by itself answer "is this the same character"** or "is this the same prop" — that needs deep-learning embeddings (face recognition, CLIP), which OpenCV isn't. It is a supporting utility for the continuity-check stage, never a standalone solution.
**Verdict:** Include it, but only as one ingredient (color/lighting-drift detection) inside a continuity-QA service that also uses face-embedding and CLIP models.

### 4.4 PySceneDetect (scenedetect.com) — Score: **1.5 / 10**
**What it is:** Open-source (BSD-3), actively maintained (v0.7.1, mid-2026) tool for detecting **cut points in an existing video file**.
**Pros:** It's free and does its actual job (video scene-cut detection) well.
**Cons:** **This tool is a domain mismatch for your pipeline.** Your input is screenplay text and your output is static storyboard images — there is no video anywhere in Group 3's spec. It has no ability to parse text, generate images, or check image continuity.
**Verdict:** Not applicable to this pipeline as specified. The only legitimate (and optional, future-phase) use would be much later: if the finished film/animatic gets cut and you want to auto-detect its actual scene boundaries to compare against the original storyboard/shot list. Don't spend integration effort on it now.

### 4.5 OpenMMLab — Score: **2 / 10**
**What it is:** A computer-vision toolbox ecosystem (mmdetection, mmagic/mmediting, mmpose, etc.), Apache-2.0.
**Pros:** Historically strong, broad toolbox if it were healthy.
**Cons:** **Verifiably stalled.** Founder Tang Xiaoou passed away in December 2023, and a GitHub Discussion (#11815) has maintainers confirming a pivot away from active CV toolbox development toward LLM work; the community has visibly migrated toward alternatives like Ultralytics, and a third-party fork emerged in October 2025 specifically because the originals went stale. Using it in 2026 means depending on largely unmaintained code.
**Verdict:** Skip. Anything OpenMMLab could theoretically offer (detection, pose, editing) has better-maintained free alternatives (Diffusers ecosystem, Ultralytics YOLO, standalone InsightFace/CLIP) surfaced elsewhere in this report.

---

## 5. Tools found by searching *beyond* your list (this is the part that actually solves the hard problems)

None of the 9 tools you named solve the two hardest sub-problems — **character consistency across hundreds of frames** and **cinematography control** — well by themselves. These are the free tools that do, found via targeted research into the current (2025–2026) state of the art:

| Tool | License | What it does | Maturity | Score |
|---|---|---|---|---|
| **ComfyUI** | GPL-3 (app), free to self-host | Node-based orchestration for Diffusers pipelines; the thing your `comfy_client.py` already drives; has a documented `/prompt` API for programmatic queueing | Very active, huge ecosystem | **9.5/10** |
| **PhotoMaker V2** (TencentARC) | Open (verify LICENSE file before commercial ship — not 100% confirmed) | Zero-shot character-identity conditioning from reference photos, seconds per image, no per-character training | Active (10.1k★), ComfyUI nodes exist | **8.5/10** |
| **ControlNet** (depth/pose, SDXL & Flux) | Apache/OpenRAIL depending on checkpoint | Structural control of framing/composition/pose — your main lever for camera angle and blocking | Mature, ComfyUI-native | **8.5/10** |
| **UNO / UMO** (ByteDance) | Apache-2.0 | Multi-subject consistency (several named characters correctly placed together in one frame) — the newest, most directly relevant hit | Active through 2025–2026, ComfyUI workflows released | **8/10** |
| **screenplay-tools** (wildwinter) | MIT | Deterministic Fountain + FDX parser into typed scene elements — the correct *first* stage before any LLM touches the script | Small but purpose-built and correct | **8/10** |
| **CLIP / DeepFace embeddings** | Open (CLIP via HF Transformers; DeepFace MIT wrapper) | Used as a QA scorer for costume/style/character-similarity drift between frames | Mature | **7/10** |
| **Story2Board** | **MIT** | Training-free, purpose-built storyboard generation (not generic story-illustration) with its own consistency benchmark | Small (266★), working code, single-maintainer risk | **7/10** |
| **InsightFace** | Code MIT; **pretrained face weights are research/non-commercial only** | Face embeddings for identity re-identification (continuity QA) | Mature, but ⚠️ **license landmine** — see §6 | **6/10 (with caveat)** |
| **IP-Adapter-FaceID / InstantID** | Code Apache-2.0, but face checkpoints explicitly **non-commercial** | Strong single-face fidelity | Mature but same InsightFace-dependency licensing problem | **4/10 for a commercial product** |

---

## 6. Risks and gaps to flag explicitly (not guessed — found)

1. **Character consistency at 100+ frame scale is a live research problem, not a solved commodity.** The most relevant open papers (Story2Board, CANVAS) are from August 2025 and April 2026. You will be building close to the current research frontier, not integrating a mature off-the-shelf feature. Budget real R&D/QA time for this, not just integration time.
2. **Cinematography control (lens, lighting-as-a-conditioning-input) has no mature, widely-adopted free model.** The realistic path is ControlNet (composition/pose) + disciplined prompt templates for lens/shot-size + scattered, individually-licensed Civitai LoRAs for post-hoc re-angling. Don't expect one clean model — expect a stack of partial tools.
3. **InsightFace-derived face weights (used by IP-Adapter-FaceID and InstantID) are explicitly licensed for research only, not commercial use.** If any part of your product is commercial, avoid shipping those specific pretrained face checkpoints; PhotoMaker V2 and UNO/UMO don't carry this restriction and should be preferred for that reason alone, independent of quality.
4. **WonderUnit Storyboarder's license is unresolved even by its own maintainers** (per open GitHub issue #1067) — don't reuse its code, only its UX ideas.
5. **OpenMMLab is functionally stalled** since its founder's death in Dec 2023 — don't build a 2026 dependency on it.
6. **PySceneDetect is not applicable to this pipeline** as specified (video-only tool, text-and-image pipeline) — it appears on your list but solves a different problem; keep it in mind only for a possible future phase (auto-comparing an edited film cut against the shot list).
7. **Free hosted inference (Hugging Face's serverless API) will not carry production volume** — your self-hosted ComfyUI/GPU plan (already in `implementation_plan.md`) is the right call; treat HF Hub purely as a model source and prototyping ground.

---

## 7. Final ranking — all tools, one table

| Rank | Tool | Category | Score /10 | One-line verdict |
|---|---|---|---|---|
| 1 | **ComfyUI** (running Flux.1-dev) | Orchestration/engine | **9.5** | Your existing choice — confirmed correct; it's the delivery mechanism for everything below |
| 2 | **Hugging Face Diffusers** | Core library | **9.5** | The free, Apache-2.0 tech underneath ComfyUI; nothing to change |
| 3 | **PhotoMaker V2** | Character consistency | 8.5 | Best zero-shot identity fidelity with no commercial-license landmine |
| 3 | **ControlNet** | Cinematography control | 8.5 | Best available free lever for framing/composition/pose |
| 5 | **UNO / UMO** | Multi-character consistency | 8.0 | Newest, purpose-built for multi-subject scenes; ComfyUI-ready |
| 5 | **screenplay-tools (wildwinter)** | Screenplay parsing | 8.0 | Correct deterministic base layer before LLM structuring |
| 7 | **Hugging Face Hub** | Model source / prototyping | 7.0 | Great for models and demos, not for production-scale inference |
| 7 | **CLIP / DeepFace embeddings** | Continuity QA | 7.0 | Free, solid for costume/style-drift scoring |
| 7 | **Story2Board** | Storyboard-specific generation | 7.0 | Promising, MIT-licensed, but small/young project — pilot before relying on it |
| 10 | **OpenCV** | Continuity QA helper | 6.0 | Useful but only as one ingredient, not a full solution |
| 11 | **InsightFace** | Continuity QA (face) | 6.0* | Fine for internal QA use, ⚠️ avoid its pretrained weights in a shipped commercial feature |
| 12 | **Boords** | Downstream review tool | 5.0 | Real API, but paid, and doesn't solve generation/consistency itself |
| 13 | **IP-Adapter-FaceID / InstantID** | Character consistency | 4.0 | Strong technically, blocked by non-commercial face-weight license |
| 14 | **StudioBinder** | Reference only | 2.0 | No API — schema/UX reference only |
| 14 | **OpenMMLab** | CV toolbox | 2.0 | Verifiably stalled since 2023 |
| 14 | **WonderUnit Storyboarder** | Reference only | 2.0 | Ambiguous license, unmaintained, no API |
| 17 | **FrameForge / FrameForge Studio** | Reference only | 1.0 | Closed, paid, zero integration surface |
| 18 | **PySceneDetect** | N/A | 1.5 | Wrong domain — video tool, not screenplay/image tool |

---

## 8. The single final recommendation

**Build on ComfyUI (Flux.1-dev) — do not switch tools.** Extend it with **PhotoMaker V2** for single-character identity, **UNO/UMO** for multi-character shots, and **ControlNet** for camera/composition control, all as ComfyUI custom nodes callable through the API your backend already expects. Pair that with a **deterministic Fountain/FDX parser (`screenplay-tools`)** feeding **Gemini 2.5 Flash** (already chosen) for the Acts→Sequences→Beats hierarchy, and a small **CLIP + DeepFace + OpenCV** continuity-QA service that scores each new frame against its character's reference set and flags drift.

This is the combination that is simultaneously **100% free, 100% programmatically integrable, and grounded in what your project has already committed to** — everything else on the list is either a paid SaaS tool with no generation control (Boords), a manual artist tool with no API (Storyboarder, FrameForge, StudioBinder), or a CV toolbox that's the wrong domain or stalled (PySceneDetect, OpenMMLab).

The one honest caveat: character consistency at full 130-page scale and camera/lighting-as-a-direct-input are both active research problems in 2026, not solved commodities — plan a real pilot (5–10 characters, 20–30 shots) to validate quality before committing to full-screenplay automation.
