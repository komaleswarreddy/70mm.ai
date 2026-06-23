import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routes import projects_router, scenes_router, shots_router, storyboards_router, ai_router, characters_router, production_router, rag_router, search_router
from app.config import settings

app = FastAPI(
    title="70MM AI API",
    description="AI-powered filmmaking workspace backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static directories
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(backend_dir, "static")
os.makedirs(os.path.join(static_dir, "storyboards"), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to 70MM AI API. Swagger UI available at /docs"}

app.include_router(projects_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")
app.include_router(shots_router, prefix="/api")
app.include_router(storyboards_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(characters_router, prefix="/api")
app.include_router(production_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(search_router, prefix="/api")

