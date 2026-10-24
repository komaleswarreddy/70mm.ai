"""
Module 44: Performance Optimisation Layer
Redis caching for hot endpoints + in-memory fallback when Redis unavailable.
Module 45: Error Handling & Self-Healing Middleware
Global error handler, retry decorators, graceful degradation.
"""
import logging
import json
import time
import functools
import asyncio
from typing import Any, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# MODULE 44 — CACHING LAYER
# ═══════════════════════════════════════════════════════════════════════════

class InMemoryCache:
    """Simple TTL-aware in-memory cache (Redis fallback)."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            value, expires_at = self._store[key]
            if time.time() < expires_at:
                return value
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        self._store[key] = (value, time.time() + ttl_seconds)

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear_prefix(self, prefix: str):
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]

    def stats(self) -> dict:
        now = time.time()
        valid = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        return {"total_keys": len(self._store), "valid_keys": valid}


class CacheManager:
    """Unified cache manager — uses Redis if available, falls back to in-memory."""

    def __init__(self):
        self._memory = InMemoryCache()
        self._redis = None
        self._redis_available = False
        self._init_redis()

    def _init_redis(self):
        try:
            import redis.asyncio as aioredis
            from app.config import settings
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            self._redis = aioredis.from_url(redis_url, decode_responses=True, socket_timeout=1)
            self._redis_available = True
            logger.info("CacheManager: Redis connected.")
        except Exception as e:
            logger.info(f"CacheManager: Redis unavailable ({e}). Using in-memory cache.")

    async def get(self, key: str) -> Optional[Any]:
        if self._redis_available:
            try:
                raw = await self._redis.get(key)
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.debug(f"Redis GET failed for {key}: {e}")
                self._redis_available = False

        return self._memory.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300):
        if self._redis_available:
            try:
                await self._redis.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception as e:
                logger.debug(f"Redis SET failed for {key}: {e}")
                self._redis_available = False

        self._memory.set(key, value, ttl)

    async def delete(self, key: str):
        if self._redis_available:
            try:
                await self._redis.delete(key)
                return
            except Exception:
                pass
        self._memory.delete(key)

    async def clear_prefix(self, prefix: str):
        if self._redis_available:
            try:
                keys = await self._redis.keys(f"{prefix}*")
                if keys:
                    await self._redis.delete(*keys)
                return
            except Exception:
                pass
        self._memory.clear_prefix(prefix)

    def stats(self) -> dict:
        return {
            "backend": "redis" if self._redis_available else "in_memory",
            **self._memory.stats(),
        }


# Singleton
_cache_manager: Optional[CacheManager] = None

def get_cache() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: int = 300, key_prefix: str = "cache"):
    """
    Async decorator that caches the return value of an async function.
    Cache key is built from prefix + function name + args.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            # Build key from args (skip 'self' / 'db' / 'request' objects)
            safe_args = []
            for a in args:
                try:
                    json.dumps(a)
                    safe_args.append(str(a))
                except Exception:
                    pass
            for k, v in kwargs.items():
                try:
                    json.dumps(v)
                    safe_args.append(f"{k}={v}")
                except Exception:
                    pass

            cache_key = f"{key_prefix}:{func.__name__}:{':'.join(safe_args)}"
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_result

            result = await func(*args, **kwargs)
            try:
                await cache.set(cache_key, result, ttl)
            except Exception as e:
                logger.debug(f"Cache SET failed: {e}")
            return result

        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 45 — ERROR HANDLING & SELF-HEALING
# ═══════════════════════════════════════════════════════════════════════════

def retry_async(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions=(Exception,)):
    """
    Async retry decorator with exponential backoff.
    Usage:
        @retry_async(max_attempts=3, delay=0.5)
        async def my_api_call():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            last_exc = None
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exc = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            logger.error(f"[{func.__name__}] All {max_attempts} attempts failed.")
            raise last_exc
        return wrapper
    return decorator


class GlobalErrorMiddleware(BaseHTTPMiddleware):
    """
    Catches all unhandled exceptions and returns structured JSON error responses.
    Includes request ID tracking and graceful degradation.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        except ValueError as e:
            logger.warning(f"[{request_id}] Validation error: {e}")
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Validation Error",
                    "detail": str(e),
                    "request_id": request_id,
                }
            )

        except PermissionError as e:
            logger.warning(f"[{request_id}] Permission error: {e}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "detail": str(e),
                    "request_id": request_id,
                }
            )

        except FileNotFoundError as e:
            logger.warning(f"[{request_id}] Not found: {e}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Resource Not Found",
                    "detail": str(e),
                    "request_id": request_id,
                }
            )

        except Exception as e:
            logger.error(f"[{request_id}] Unhandled exception on {request.url}: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred. The team has been notified.",
                    "request_id": request_id,
                    "fallback": True,
                }
            )


class HealthRouter:
    """System health and diagnostics endpoints."""

    @staticmethod
    def create_router():
        from fastapi import APIRouter
        router = APIRouter(prefix="/health", tags=["health"])

        @router.get("/")
        async def health_check():
            """Basic health check."""
            return {
                "status": "healthy",
                "service": "70MM AI Backend",
                "timestamp": time.time(),
            }

        @router.get("/cache")
        async def cache_health():
            """Cache layer status."""
            cache = get_cache()
            return {
                "status": "ok",
                "cache": cache.stats(),
            }

        @router.get("/full")
        async def full_health():
            """Full system health check."""
            checks = {}

            # DB check
            try:
                from app.database import engine
                async with engine.connect() as conn:
                    await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
                checks["database"] = "healthy"
            except Exception as e:
                checks["database"] = f"error: {e}"

            # Cache check
            cache = get_cache()
            checks["cache"] = cache.stats()

            # AI service check (no network call — just verify importable)
            try:
                from app import ai_service
                checks["ai_service"] = "importable"
            except Exception as e:
                checks["ai_service"] = f"error: {e}"

            all_healthy = all(
                isinstance(v, (dict, str)) and "error" not in str(v)
                for v in checks.values()
            )

            return {
                "status": "healthy" if all_healthy else "degraded",
                "checks": checks,
                "timestamp": time.time(),
            }

        return router


health_router = HealthRouter.create_router()
