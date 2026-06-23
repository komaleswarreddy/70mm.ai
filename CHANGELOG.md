# CHANGELOG — 70MM AI

All notable changes to **70MM AI** are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] — 2026-06-23 — PRODUCTION RELEASE

### 🎬 Core Platform (Stages 1–3)

#### Added
- **Project CRUD** — Create, read, update, soft-delete, duplicate projects
- **Scene Parser** — Fountain/FDX/plain-text screenplay parser extracting scenes, action blocks, dialogues, characters
- **Character Bible** — Full character profiles with traits, arcs, backstory, relationships, visual consistency
- **Shot Planner** — Shot list editor with shot size, lens, angle, movement, emotion, colour palette
- **Storyboard Generator** — AI-powered storyboard frame generation via ComfyUI / Stable Diffusion
- **Director's Muse** — Director-style composition guidance (Kubrick, Villeneuve, Nolan, Wong Kar-Wai, Coppola, Scorsese)
- **Story Engine** — Idea → premise → synopsis → beat sheet → act structure via multi-model AI routing
- **Export System** — PDF + CSV exports for entire project, scene breakdown, shot list

---

## [1.9.0] — Stage 4: AI Intelligence Modules

### Added
- **Module 31: Character Consistency Engine** — InstantID + IP-Adapter face/hair/costume lock for storyboard generation
- **Module 32: Redis + Celery Background Engine** — Async task queues for storyboard, export, RAG indexing, notifications
- **Module 33: True Cinematic RAG Engine** — ChromaDB vector store with LangChain retrieval over screenwriting literature
- **Module 34: Cross-Project Search** — Full-text search across projects, scenes, shots with global search endpoint
- **Module 35: Director Mode Pro** — Frame analysis, composition overlay, reference gallery, moodboard viewer
- **Module 36: Multimodal Input Engine** — Voice-to-screenplay transcription, moodboard colour extraction, image scene analysis
- **Module 37: Visual Reference Library** — Gallery, collections, favourites, reference card browser

---

## [1.8.0] — Stage 3: Production Tools

### Added
- **Module 22: Production Planner** — Call sheets, daily schedule, budget tracker, collaborator comments
- **Module 23: Version History** — Project snapshots, restore points, diff viewer
- **Module 24: Collaboration Layer** — Scene-level comments, role-based annotations
- **Module 25: Animatics Timeline** — Frame-by-frame shot animation timeline with playhead
- **Module 26: QA Dashboard** — Continuity warnings, missing coverage, shot validation
- **Module 27: Collaborative Agents** — AI Story/Character/Scene agent collaboration panel
- **Module 28: Scene Inspector** — In-depth scene analysis with action, dialogue, continuity breakdown
- **Module 29: Plugins Container** — Plugin API for external tool integration
- **Module 30: Relationship Graph** — SVG-based character relationship visualisation

---

## [1.5.0] — Stage 2: Screenplay Workflow

### Added
- **Module 11: Scene Cards** — Drag-and-drop visual scene overview
- **Module 12: Story Timeline** — Horizontal beat-sheet timeline with act markers
- **Module 13: Script Editor** — Inline screenplay editor with Fountain syntax support
- **Module 14: Continuity Panel** — Cross-scene continuity analysis
- **Module 15: Storyboard Timeline** — Horizontal storyboard strip with thumbnail frames
- **Module 16: Director Monitor** — Live production monitoring dashboard
- **Module 17: Knowledge Base** — Semantic search over RAG documents
- **Module 18: Task Queue Panel** — Background task monitoring UI
- **Module 19: Navbar + Sidebar** — Global navigation with project switcher
- **Module 20: Auth Provider** — Firebase Auth integration with mock token fallback
- **Module 21: RAG Search** — Integrated RAG semantic search panel

---

## [2.0.0] — Stage 5: Finalisation & Release (THIS RELEASE)

### Added
- **Module 38: E2E Workflow Verification** — 16-step end-to-end test covering full project lifecycle
- **Module 39: Full System Integration Tests** — Inter-module cascade, chain, reorder, search, batch tests
- **Module 40: Agent Coordinator** — Shared memory context, grounded prompt building, multi-agent routing
- **Module 41: Cinematic Copilot** — Inline scene suggestions: camera, blocking, emotion, transitions + AI tip
- **Module 42: Script Doctor** — Structural analysis: act diagnosis, pacing, stakes, theme alignment, RAG citations
- **Module 43: Background Task Validation** — Health endpoints for cache and full system status
- **Module 44: Performance Optimisation** — Redis caching with in-memory fallback, `@cached()` decorator
- **Module 45: Error Handling & Self-Healing** — GlobalErrorMiddleware, `@retry_async()` decorator, structured error responses
- **Module 46: UI Polish** — Skeleton loaders (all views), empty state components (all views)
- **Module 47: Comprehensive Test Suite** — 35+ tests across agents, copilot, script doctor, middleware, parser
- **Module 48: Release Candidate** — CHANGELOG, README, docker-compose, architecture diagram

### Fixed
- SQLAlchemy `MissingGreenlet` error in `duplicate_project` — IDs now captured immediately after `db.refresh()` in async context
- FastAPI route ordering in `shots.py` — `PUT /batch` now registered before `PUT /{id}` to prevent 404
- Search route `/api/search/` unified endpoint added for cross-entity global search
- Parser test assertions aligned with actual parser character name output

### Performance
- Hot endpoints cacheable with `@cached(ttl=300)` decorator
- Redis backend with graceful fallback to in-memory TTL cache
- `X-Request-ID` header injected on every response for distributed tracing

---

## Architecture

```
Backend:  FastAPI + SQLAlchemy (async) + SQLite (dev) / PostgreSQL (prod)
Queue:    Celery + Redis
AI:       OpenAI GPT-4o → Gemini 2.5 Flash → Ollama (fallback chain)
RAG:      ChromaDB + LangChain + Cinematic literature embeddings
Images:   ComfyUI / Stable Diffusion (local) + Fal.ai (cloud fallback)
Auth:     Firebase Admin + Mock token (dev)
Frontend: Next.js 14 App Router + Tailwind CSS + Framer Motion
```

---

*Maintained by the 70MM AI team — Built for filmmakers, by storytellers.*
