"""
FastAPI main application — Texie backend.

Startup:
  1. Creates database tables
  2. Seeds exactly two authorized users
  3. Starts WebSocket + REST API server
"""
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database.session import create_tables, AsyncSessionLocal
from backend.database.repository import UserRepository
from backend.auth.authentication import hash_password
from backend.auth.routes import router as auth_router
from backend.chat.routes import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def seed_users() -> None:
    """
    Ensure exactly two users exist in the database.
    Only runs on startup; safe to call repeatedly.
    """
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)

        for username, password in [
            (settings.USER_A_USERNAME, settings.USER_A_PASSWORD),
            (settings.USER_B_USERNAME, settings.USER_B_PASSWORD),
        ]:
            existing = await repo.get_by_username(username)
            if not existing:
                await repo.create(username=username, hashed_password=hash_password(password))
                logger.info(f"[SEED] Created user: {username}")
            else:
                logger.info(f"[SEED] User already exists: {username}")

        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("[STARTUP] Creating database tables...")
    await create_tables()
    logger.info("[STARTUP] Seeding authorized users...")
    await seed_users()
    logger.info("[STARTUP] Texie backend ready.")
    yield
    logger.info("[SHUTDOWN] Texie backend shutting down.")


app = FastAPI(
    title="Texie — Private Messenger Backend",
    description="Secure two-person messaging relay. Messages stored encrypted only.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# CORS — restrict to known origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "texie-backend"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )
