# 70MM.ai — AI Storyboard & Cinematography Engine

<p align="center">
  <img src="complete_reference_storyBoard.png" alt="70MM.ai Storyboard Sheet Preview" width="100%" />
</p>

<p align="center">
  <strong>Transform screenplays into production-ready director board sheets, cinematographic shot plans, and character-consistent photorealistic frames.</strong>
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/Next.js-16_Turbopack-black?logo=next.js" alt="Next.js" /></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/FastAPI-0.111.0-009688?logo=fastapi" alt="FastAPI" /></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python" alt="Python" /></a>
  <a href="#technology-stack"><img src="https://img.shields.io/badge/ComfyUI-Flux.1_dev_fp8-blueviolet" alt="ComfyUI" /></a>
  <a href="#character-consistency-engine"><img src="https://img.shields.io/badge/Consistency-ByteDance_USO-orange" alt="ByteDance USO" /></a>
  <a href="#testing"><img src="https://img.shields.io/badge/Tests-Passing-success" alt="Tests" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-blue" alt="License" /></a>
</p>

---

## 🎬 Overview

**70MM.ai** is an end-to-end AI cinematography platform that turns screenplays (**Fountain, Final Draft FDX, PDF, or plain text**) into complete, production-grade director board sheets:
1. **Screenplay ingestion & parsing**: Identifies scenes, sluglines, actions, dialogues, characters, and scene transitions.
2. **Dramatic structuring**: Decomposes scenes into acts, sequences, and narrative beats.
3. **Scene understanding**: Extracts emotional subtext, mood, visual pacing, and lighting ambiance.
4. **Automated shot breakdown**: Divides scenes into sequential camera setups (wide, medium, close-up, over-the-shoulder, etc.).
5. **6-axis cinematography planning**: Computes camera lens (mm), camera angle, camera movement, lighting style, depth-of-field, and color palette.
6. **Character asset locking**: Establishes reference portraits, fixed random seeds, and identity embeddings (OpenCV YuNet + SFace, CLIP) to guarantee facial identity across shots.
7. **Photorealistic shot generation**: Dispatches deterministic prompt structures to ComfyUI running Flux.1-dev (fp8) with ByteDance USO multi-reference latent conditioning on cloud or local GPUs.
8. **Production board compositing**: Generates ultra-high-resolution (7200px) print-ready sheets and vector PDFs featuring scene color banners, airmail headers, shot numbers, dialogue captions, lens/movement tags, cast cards, and complex script rendering (e.g., Telugu shaped with HarfBuzz/raqm).
9. **Continuity QA**: Validates visual consistency across shots via OpenCV color histogram Bhattacharyya distance, CLIP style drift, and facial recognition scoring.
10. **Natural-language director editor**: Allows interactive, conversational adjustments to any shot's cinematography or layout.

> 📖 **Deep Dive Documentation:** For the full story, technical benchmarks, and architectural design rationale, see **[architecture.md](architecture.md)** and **[STORYBOARD_ENGINE_MASTER_PROMPT.md](STORYBOARD_ENGINE_MASTER_PROMPT.md)**.

---

## 📑 Table of Contents

- [The 10-Stage Pipeline](#-the-10-stage-pipeline)
- [Technology Stack](#-technology-stack)
- [Architecture & Key Design Decisions](#-architecture--key-design-decisions)
- [Project Structure](#-project-structure)
- [Quick Start Guide](#-quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Backend Setup](#3-backend-setup)
  - [4. Frontend Setup](#4-frontend-setup)
  - [5. GPU Image Generation Backend (ComfyUI)](#5-gpu-image-generation-backend-comfyui)
  - [6. Docker Compose Deployment](#6-docker-compose-deployment)
- [Character Consistency Engine](#-character-consistency-engine)
- [Board Compositing & Production Studio](#-board-compositing--production-studio)
- [Testing](#-testing)
- [Challenges Faced & Solutions](#-challenges-faced--solutions)
- [Troubleshooting Cheat-Sheet](#-troubleshooting-cheat-sheet)

---

## 🚀 The 10-Stage Pipeline

Each stage is modular, independently callable through dedicated REST endpoints, and decoupled from long-running background tasks.

| Stage | Name | Description | Key Modules | Primary Endpoint |
|---|---|---|---|---|
| **1** | **Parse** | Ingests Fountain, FDX, PDF, or text into structured scenes, action blocks, and characters | `parser.py`, `universal_importer.py` | `POST /api/projects/{id}/parse` |
| **2** | **Structure** | Analyzes acts, sequences, and dramatic narrative beats | `ai_service.py` | `POST /api/projects/{id}/structure` |
| **3** | **Scene Understanding** | Computes visual emphasis, subtext, mood, and dramatic pacing | `ai_service.py` | `POST /api/scenes/{id}/understand` |
| **4** | **Shot Division** | Rules-based shot list generation (framing, reasoning, screen direction) | `shot_planner.py`, `ai_service.py` | `POST /api/scenes/{id}/shots/generate-plan` |
| **5** | **Cinematography Plan** | Defines camera lens, angle, movement, lighting ratio, DOF, and color grading | `shot_planner.py`, `ai_service.py` | Embedded in Stage 4 |
| **6** | **Character Assets** | Generates & locks 1–4 reference portraits, fixed seeds, and CLIP/SFace identity embeddings | `character_asset_service.py`, `face_identity.py` | `POST /api/characters/{id}/lock-reference` |
| **7** | **Image Generation** | Builds deterministic prompts and ComfyUI node graphs (Flux.1-dev fp8 + USO) with Pillow fallback | `shot_prompt_builder.py`, `comfy_workflow_builder.py`, `stage7_orchestrator.py` | `POST /api/shots/{id}/generate-image` |
| **8** | **Board Compositing** | Assembles 7200px PNG sheets & vector PDFs with airmail borders, Telugu script shaping, and shot metadata | `board_service.py`, `board-studio.tsx` | `POST /api/projects/{id}/boards/compose` |
| **9** | **Continuity QA** | Evaluates facial similarity (SFace), color grading (Bhattacharyya), and style drift (CLIP) | `continuity_service.py`, `embedding_service.py`, `image_qa.py` | `POST /api/shots/{id}/continuity-check` |
| **10** | **Director Editor** | Applies free-text director instructions to modify camera, lighting, and composition | `ai_service.py` | `PATCH /api/shots/{id}/edit` |

**Supporting Systems:**
- **Director's Muse & AI Tools**: Composition suggestions, rule-of-thirds overlays, prompt previews (`ai_tools.py`).
- **Cinematic Copilot Engine**: Real-time script feedback and scene enhancement (`copilot_engine.py`).
- **Script Doctor**: Diagnostic breakdown of narrative pacing, dialogue-to-action ratios, and character arcs (`script_doctor.py`).
- **Production Office**: Call sheets, schedule estimation, and document export in PDF/CSV/DOCX (`production.py`, `export_service.py`).
- **Self-Healing & Redis Cache**: SHA-256 fingerprint caching for fast re-renders and auto-retry middleware (`middleware.py`).

---

## 🛠 Technology Stack

### Backend
- **FastAPI 0.111.0 + Uvicorn**: High-performance asynchronous REST API.
- **SQLAlchemy 2.0 (Async) + asyncpg**: Asynchronous ORM with PostgreSQL (and seamless SQLite fallback for local development).
- **Celery 5.4 + Redis**: Distributed task queues for shot generation, QA checks, and export rendering.
- **Pillow & ReportLab**: Dual-renderer pipeline for pixel-perfect 7200px production PNGs and print-ready vector PDFs.
- **PyMuPDF (`fitz`), `python-docx`, `fountain`**: Screenplay document ingestion.

### AI & Vision Models
- **Primary LLM**: **Groq** (`openai/gpt-oss-120b` for reasoning and structuring, `qwen/qwen3.8-27b` for multimodal vision QA). High throughput, low latency. Secondary fallback to OpenAI or local Ollama.
- **Base Diffusion Model**: **Flux.1-dev (fp8)**: State-of-the-art open-weights image generation running within 15GB VRAM.
- **Character Consistency**: **ByteDance USO (Unified Subject Operator)**: Native ComfyUI core nodes (`ReferenceLatent` + `FluxKontextMultiReferenceLatentMethod`) with zero custom-node dependencies.
- **Face Detection & Recognition**: **OpenCV YuNet** (MIT) + **OpenCV SFace** (Apache 2.0) running locally from `backend/models/opencv/` (Cosine similarity threshold: 0.363).
- **Landmark Detection**: **MediaPipe Face & Hand Landmark Tasks** running locally from `backend/models/mediapipe/`.
- **Visual & Style Embeddings**: **OpenAI CLIP ViT-B/32** via `open_clip_torch` for scene continuity and style-drift detection.

### Frontend
- **Next.js 16 (App Router + Turbopack)** + **React 19** + **TypeScript**.
- **Tailwind CSS 4**: Modern styling with custom dark cinematography studio aesthetic.
- **Board Studio Component**: Interactive canvas preview for inspecting composed panels, adjusting crop reframings, editing captions, and triggering downloads.
- **Firebase Auth**: Authentication and user session management.

---

## 🏗 Architecture & Key Design Decisions

### 1. Deterministic Prompt Engineering, Not Prose Hallucination
Shot generation prompts are built by a deterministic, byte-reproducible pure function (`shot_prompt_builder.py`). Cinematography parameters (lens mm, lighting ratio, camera height, depth of field) map to exact film terms (e.g., *"35mm anamorphic, f/2.8, shallow depth of field, warm key light, cinematic film still"*). LLM prose is never directly passed to the diffusion model, eliminating stylistic drift and hallucinated artifacts.

### 2. Dual-Engine Board Layout (Pillow + ReportLab)
A single layout calculator determines all bounding boxes in virtual design coordinates. The layout is then rendered in parallel by:
- **Pillow**: Emits a 7200px master PNG board sheet.
- **ReportLab**: Emits a scalable vector PDF with high-resolution image embeds.
- **Complex Script Typesetting**: Non-Latin scripts (e.g., Telugu letters shaped with HarfBuzz/raqm) are rasterized at high DPI with alpha transparency and composited cleanly into both PDF and PNG formats.

### 3. SHA-256 Fingerprint Caching
Re-composing an unchanged project takes **< 1.0 second** (down from 92 seconds). The engine hashes all shot crops, dialogue lines, lens metadata, image modification timestamps, and board settings into a SHA-256 fingerprint. If inputs have not changed, cached assets are returned instantly.

### 4. Zero Silent Failures (Pillow Fallback)
If ComfyUI is offline, unreachable, or exhausts retries, `image_service.py` renders a clean, clearly labeled placeholder frame displaying the shot metadata. This allows script parsing, shot planning, and board layout to be tested end-to-end even when no GPU is available.

---

## 📁 Project Structure

```
70MM.ai/
├── backend/
│   ├── app/
│   │   ├── routes/                      # REST endpoints (projects, scenes, shots, characters, etc.)
│   │   ├── character_consistency/       # ByteDance USO client & consistency manager
│   │   ├── rag/                         # Screenwriting knowledge base & retrieval
│   │   ├── ai_service.py                # LLM orchestration & Groq fallback chain
│   │   ├── board_service.py             # Stage 8: 7200px PNG & vector PDF board compositor
│   │   ├── character_asset_service.py   # Stage 6: Reference portrait locking & seed pinning
│   │   ├── comfy_client.py              # Asynchronous HTTP/WebSocket client for ComfyUI
│   │   ├── comfy_workflow_builder.py    # ComfyUI prompt node-graph builder (Flux + USO)
│   │   ├── config.py                    # Pydantic Settings configuration
│   │   ├── continuity_service.py        # Stage 9: Color & style continuity validation
│   │   ├── copilot_engine.py            # AI Director Copilot suggestions
│   │   ├── database.py                  # Async SQLAlchemy session & engine
│   │   ├── embedding_service.py         # OpenCLIP visual embedding extractor
│   │   ├── export_service.py            # PDF/CSV screenplay & shot list export
│   │   ├── face_identity.py             # OpenCV YuNet detection & SFace feature matching
│   │   ├── image_qa.py                  # MediaPipe landmark check & vision model review
│   │   ├── image_service.py             # High-level shot generation orchestrator & fallback
│   │   ├── models.py                    # SQLAlchemy database models
│   │   ├── parser.py                    # Stage 1: Fountain & script parsing
│   │   ├── schemas.py                   # Pydantic request/response schemas
│   │   ├── script_doctor.py             # Screenplay diagnostic & structural analysis
│   │   ├── shot_planner.py              # Stage 4/5: Rules-based shot division & camera plan
│   │   ├── shot_prompt_builder.py       # Stage 7: Deterministic camera prompt compiler
│   │   ├── stage7_orchestrator.py       # Stage 7: Pipeline coordinator
│   │   └── universal_importer.py        # Final Draft (.fdx) & PDF import parser
│   ├── models/                          # Local computer-vision models
│   │   ├── mediapipe/                   # Face & hand landmarker .task files
│   │   └── opencv/                      # YuNet face detector & SFace recognizer ONNX
│   ├── static/                          # Runtime static directories (.gitkeep preserved)
│   │   ├── boards/                      # Composed production board sheets
│   │   ├── character_refs/              # Character reference portraits
│   │   └── storyboards/                 # Generated shot frames
│   ├── tests/                           # Pytest test suite (21 test files + fixtures)
│   │   └── fixtures/                    # Sample .fdx, .fountain, and screenplay texts
│   ├── Dockerfile                       # Production backend Docker container
│   ├── pytest.ini                       # Test configuration (asyncio_mode = auto)
│   └── requirements.txt                 # Backend Python dependencies
├── frontend/
│   ├── app/                             # Next.js 16 App Router pages
│   │   ├── workspace/[projectId]/       # Main interactive production studio
│   │   └── projects/                    # Project selection and management
│   ├── components/                      # UI components
│   │   ├── board-studio.tsx             # Interactive production board canvas & viewer
│   │   ├── character-bible/             # Character consistency & portrait locking
│   │   ├── scene-cards.tsx              # Scene breakdown & narrative beat views
│   │   ├── shot-planner.tsx             # Cinematography planner & lens selectors
│   │   ├── storyboard-timeline.tsx      # Sequential shot frame viewer & re-generator
│   │   └── qa-dashboard.tsx             # Continuity & face identity analytics
│   ├── lib/
│   │   └── api.ts                       # Fully-typed API client for all backend endpoints
│   ├── package.json
│   └── tsconfig.json
├── kaggle_comfyui_setup/                # ComfyUI + Flux.1 + USO setup notebook for Kaggle T4 GPU
├── docker-compose.yml                   # Complete production orchestration
├── architecture.md                      # Comprehensive architecture guide & development journey
└── README.md                            # Main project documentation
```

---

## ⚡ Quick Start Guide

### Prerequisites
- **Python 3.12+**
- **Node.js 20+** and **npm 10+**
- **PostgreSQL** (optional: falls back to local SQLite if `DATABASE_URL` is omitted)
- **Groq API Key** (Free tier available at [console.groq.com](https://console.groq.com))
- *(Optional for real GPU image generation)*: A free Kaggle account or a local GPU machine with 16GB+ VRAM running ComfyUI.

---

### 1. Clone Repository

```bash
git clone https://github.com/komaleswarreddy/70mm.ai.git
cd 70mm.ai
```

---

### 2. Environment Configuration

#### Backend Configuration (`backend/.env`)
Copy the example environment file:
```bash
cp backend/.env.example backend/.env
```
Populate `backend/.env` with your credentials:

```ini
# Database: Leave blank for local SQLite, or provide Postgres async connection string
DATABASE_URL=sqlite+aiosqlite:///./70mm.db
# Or: postgresql+asyncpg://postgres:password@localhost:5432/seventy_mm

# Primary LLM Provider: Groq (free, ultra-fast)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Optional Fallbacks
OPENAI_API_KEY=
OLLAMA_URL=http://localhost:11434

# GPU Backend: URL of ComfyUI (Local or Cloudflare Tunnel from Kaggle)
COMFYUI_URL=https://your-tunnel-name.trycloudflare.com

# Server Bind Settings
HOST=0.0.0.0
PORT=8000
```

#### Frontend Configuration (`frontend/.env.local`)
Create `frontend/.env.local` (optional, defaults to `http://localhost:8000/api`):
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify backend health:
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### 4. Frontend Setup

In a new terminal:
```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to open the 70MM.ai Workspace.

---

### 5. GPU Image Generation Backend (ComfyUI)

If you have a local GPU (RTX 3090/4080/4090 or better), point `COMFYUI_URL` directly to `http://localhost:8188`.

To run on a free Kaggle Tesla T4 GPU (30 hours/week free tier):

1. Install the Kaggle CLI: `pip install kaggle` and place your `kaggle.json` in `~/.kaggle/`.
2. Push the notebook to Kaggle:
   ```bash
   cd kaggle_comfyui_setup
   kaggle kernels push -p .
   ```
3. Check status and fetch the Cloudflare tunnel URL:
   ```bash
   kaggle kernels status krkomaleswarreddy/comfyui-flux-uso-setup
   kaggle kernels logs krkomaleswarreddy/comfyui-flux-uso-setup | grep "trycloudflare.com"
   ```
4. Copy the printed `https://<unique-id>.trycloudflare.com` URL into `backend/.env` as `COMFYUI_URL` and restart your backend.

> 💡 **Note:** When ComfyUI is not connected, 70MM.ai automatically uses Pillow to generate placeholder frames with complete shot metadata, allowing full testing of the pipeline without a GPU.

---

### 6. Docker Compose Deployment

To run the complete production stack (PostgreSQL, Redis, FastAPI, Celery worker, and Next.js):

```bash
# Prepare environment files
cp backend/.env.example backend/.env
# Edit backend/.env with your GROQ_API_KEY

# Build and start all services
docker compose up --build
```

---

## 🎭 Character Consistency Engine

Facial and stylistic continuity is maintained through a three-layer verification system:

```
[Screenplay Character Description]
                │
                ▼
   [Stage 6: Character Portrait Generation]
                │
                ▼
   [Lock Reference Images + Seed Pinning]
                │
     ┌──────────┴──────────┐
     ▼                     ▼
[OpenCV SFace/YuNet]  [OpenCLIP ViT-B/32]
512-d Facial Vector   512-d Global Embedding
     │                     │
     └──────────┬──────────┘
                ▼
[Stage 7: Flux.1-dev + ByteDance USO Multi-Reference]
                │
                ▼
[Stage 9: Quality & Identity QA Gatekeeper]
```

1. **Character Asset Locking**: Generates canonical multi-angle portraits and extracts 512-dimensional facial embedding vectors using local OpenCV SFace models (`backend/models/opencv/face_recognition_sface_2021dec.onnx`).
2. **ByteDance USO Conditioning**: Passes reference latents directly into Flux's DiT backbone via native ComfyUI core nodes (`ReferenceLatent` + `FluxKontextMultiReferenceLatentMethod`), preserving character features without third-party node fragility.
3. **Automated Verification**: Generated shots are analyzed by OpenCV YuNet to detect faces and SFace to evaluate cosine similarity against the character's locked reference set (threshold: `0.363`).

---

## 🎨 Board Compositing & Production Studio

Stage 8 (`board_service.py` & `board-studio.tsx`) turns raw frames into cinema-grade production storyboard sheets:

- **Ultra-High Resolution**: 7200 × 4050 px 300 DPI master sheet output.
- **Airmail Production Frame**: Classic border styling with scene index flags, project titles, and director legends.
- **Telugu & Non-Latin Font Shaping**: Integrated with HarfBuzz/raqm for accurate rendering of complex scripts (e.g., Telugu title and taglines).
- **Dual Vector / Raster Output**: Produces both full-resolution PNG sheets and print-ready vector PDF documents with embedded metadata.
- **Board Studio UI**: Interactive preview in Next.js with pan/zoom controls, caption editing, reframing crops, and PDF export.

---

## 🧪 Testing

The repository includes a comprehensive test suite across the backend and frontend:

### Backend Tests (Pytest)
```bash
cd backend
python -m pytest tests/ -v
```
- **21 test suites** covering script parsing, FDX import, shot planning, prompt builders, ComfyUI workflow generation, board compositing, face identity, and continuity checks.
- Runs with in-memory SQLite and mock fixtures; no external API or GPU required.

### Frontend Type Validation
```bash
cd frontend
npx tsc --noEmit
```
- Validates full TypeScript type safety across all React components and API client bindings.

---

## 💡 Challenges Faced & Solutions

| Challenge | Root Cause | Solution |
|---|---|---|
| **ComfyUI RAM OOM / SIGKILL** | Running plain Flux alongside character-conditioned (USO) workflows cached both models in system RAM simultaneously. | Implemented family-switch tracking in `comfy_client.py`: triggers ComfyUI's `/free` endpoint only when switching model pipelines. |
| **Cloudflare Tunnel False-Negatives** | Quick tunnel transient latency blips triggered premature offline status in single-attempt health checks. | Upgraded `ComfyClient.is_healthy()` to dual-attempt check with an 8-second timeout window. |
| **SQLAlchemy `MissingGreenlet`** | Accessing ORM attributes after `await db.commit()` without refreshing triggered synchronous lazy loads in async context. | Captured plain values into local variables prior to commit, or explicitly called `await db.refresh(obj)`. |
| **FastAPI Multipart File Validation** | FastAPI 0.111.0 failed multipart validation when using `Optional[List[UploadFile]] = File(None)`. | Refactored character reference endpoints to accept four explicit named `Optional[UploadFile]` arguments. |
| **Telugu Complex Script Distortion** | Standard PIL rasterizers fail complex ligatures and character shaping for Indic scripts. | Enabled HarfBuzz/raqm text layout engine for Telugu rendering, rasterized as high-DPI transparent layers for PDF inclusion. |

---

## 🔧 Troubleshooting Cheat-Sheet

| Symptom | Cause | Resolution |
|---|---|---|
| `ModuleNotFoundError: No module named '...'` | Multiple Python environments on system PATH. | Activate the dedicated project virtual environment (`venv\Scripts\activate` or `source venv/bin/activate`). |
| Generated images are colored placeholders with text | ComfyUI is offline or tunnel URL changed. | Normal behavior when GPU is offline. Update `COMFYUI_URL` in `backend/.env` with active tunnel URL. |
| `kaggle kernels status` returns permission denied | Stale kernel slug in `kaggle_comfyui_setup/kernel-metadata.json`. | Run `kaggle kernels list -m` to check your actual kernel name and ensure `id` matches in `kernel-metadata.json`. |
| Compose takes >60 seconds on repeated calls | Cache fingerprint invalidated by file modification timestamp drift. | Keep file modifications static; unchanged projects return in `< 1.0s` from SHA-256 fingerprint cache. |

---

## 📄 License

This project is licensed under the **MIT License**.

- OpenCV YuNet: **MIT License**
- OpenCV SFace: **Apache 2.0 License**
- ByteDance USO: **Apache 2.0 License**
- Flux.1-dev: **FLUX.1 [dev] Non-Commercial License** (open weights)

---

<p align="center">
  Built with ❤️ for filmmakers, directors, and cinematographers by the <strong>70MM.ai</strong> team.
</p>
