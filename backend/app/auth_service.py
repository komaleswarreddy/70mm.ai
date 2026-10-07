# Auth Service Module
import os
import logging
from pathlib import Path
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth

logger = logging.getLogger(__name__)

# ── Load .env manually so os.getenv works before pydantic-settings does ───────
def _load_env_file():
    """Parse the backend .env file and populate os.environ for any missing keys."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Only set if not already in environment (allow real env vars to override)
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as exc:
        logger.warning(f"Could not parse .env file: {exc}")

_load_env_file()

# ── Firebase Admin SDK initialization ─────────────────────────────────────────
firebase_initialized = False
firebase_project_id: str | None = None

try:
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

    # Resolve relative paths relative to the backend directory (parent of app/)
    if cred_path and not os.path.isabs(cred_path):
        cred_path = str(Path(__file__).parent.parent / cred_path)

    logger.info(f"[Auth] FIREBASE_CREDENTIALS_PATH resolved to: {cred_path}")

    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        # Read project_id from certificate for diagnostic logging
        import json
        with open(cred_path) as f:
            _sa = json.load(f)
        firebase_project_id = _sa.get("project_id")
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        logger.info(f"[Auth] Firebase Admin initialized via certificate. Project: {firebase_project_id}")
    else:
        logger.warning(f"[Auth] Credential file not found at '{cred_path}'. Trying Application Default Credentials.")
        firebase_admin.initialize_app()
        firebase_initialized = True
        logger.info("[Auth] Firebase Admin initialized via Application Default Credentials.")

except Exception as e:
    logger.warning(
        f"[Auth] Firebase Admin initialization failed: {str(e)}. "
        "Running in Mock Auth fallback mode."
    )

logger.info(f"[Auth] firebase_initialized={firebase_initialized}, project_id={firebase_project_id}")

# ── Security dependency ────────────────────────────────────────────────────────
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials

    logger.debug(
        f"[Auth] Token received — type={'mock' if token.startswith('mock_') else 'firebase'}, "
        f"firebase_initialized={firebase_initialized}"
    )

    # ── Mock / demo token path ─────────────────────────────────────────────────
    if token.startswith("mock_"):
        if token == "mock_vasu_token_xyz":
            logger.info("[Auth] Mock token validated for user: vasu")
            return {
                "uid": "uid_vasu",
                "email": "vasu@70mm.ai",
                "name": "vasu",
                "role": "director",
                "scopes": ["admin", "director", "writer"],
            }
        else:
            logger.warning(f"[Auth] Unknown mock token rejected: {token[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid mock token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # ── Firebase JWT path ──────────────────────────────────────────────────────
    if not firebase_initialized:
        logger.error("[Auth] Firebase not initialized — cannot verify JWT token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication service unavailable. Please use demo credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        logger.info(f"[Auth] Firebase JWT verified for uid={uid}")
        return {
            "uid": uid,
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name") or decoded_token.get("email"),
        }
    except Exception as e:
        logger.error(f"[Auth] Firebase token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

