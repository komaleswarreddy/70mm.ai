import os
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth

logger = logging.getLogger(__name__)

firebase_initialized = False
try:
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        logger.info("Firebase Admin initialized via certificate file.")
    else:
        # Try default credential initialization
        firebase_admin.initialize_app()
        firebase_initialized = True
        logger.info("Firebase Admin initialized.")
except Exception as e:
    logger.warning(f"Firebase Admin initialization skipped: {str(e)}. Running in Mock Auth fallback mode.")

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    
    if not firebase_initialized or token.startswith("mock_"):
        # Local mock token validation
        if token == "mock_vasu_token_xyz":
            return {
                "uid": "uid_vasu",
                "email": "vasu@70mm.ai",
                "name": "vasu",
                "role": "director",
                "scopes": ["admin", "director", "writer"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token",
                headers={"WWW-Authenticate": "Bearer"},
            )

            
    try:
        decoded_token = auth.verify_id_token(token)
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name")
        }
    except Exception as e:
        logger.error(f"Firebase token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
