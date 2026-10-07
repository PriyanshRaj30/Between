"""
Application configuration using pydantic-settings.
Reads from .env file automatically.
"""
from pydantic_settings import BaseSettings
import secrets
import os


def _get_or_create_secret_key() -> str:
    """
    Generate SECRET_KEY once and persist it to a local file.
    This ensures JWTs remain valid across backend restarts.
    If a .env file sets SECRET_KEY explicitly, that takes priority.
    """
    key_file = os.path.join(os.path.dirname(__file__), ".secret_key")
    if os.path.exists(key_file):
        with open(key_file) as f:
            key = f.read().strip()
            if key:
                return key
    key = secrets.token_hex(32)
    with open(key_file, "w") as f:
        f.write(key)
    return key


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://texie_user:texie_pass@localhost:5432/texie_db"

    # JWT
    SECRET_KEY: str = _get_or_create_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 86400

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    # Two authorized users (seeded on startup)
    USER_A_USERNAME: str = "user_a"
    USER_A_PASSWORD: str = "change_this_password_a"
    USER_B_USERNAME: str = "user_b"
    USER_B_PASSWORD: str = "change_this_password_b"

    # Shared conversation ID for the two-person chat
    CONVERSATION_ID: str = "texie_private_conversation"

    model_config = {"env_file": "backend/.env", "extra": "ignore"}


settings = Settings()
