"""
Auth routes: login, token refresh, public key exchange.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from backend.database.session import get_db
from backend.database.repository import UserRepository
from backend.auth.authentication import verify_password, create_access_token, decode_token
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str


class PublicKeyUpdate(BaseModel):
    public_key: str


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint — returns JWT access token.
    Only two pre-configured users can authenticate.
    """
    repo = UserRepository(db)
    user = await repo.get_by_username(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await repo.update_last_seen(user.id)
    token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS),
    )
    return Token(access_token=token, token_type="bearer", username=user.username)


@router.put("/public-key")
async def update_public_key(
    payload: PublicKeyUpdate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload device's public key for E2E encryption key exchange.
    """
    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")

    repo = UserRepository(db)
    import uuid
    await repo.update_public_key(uuid.UUID(data["sub"]), payload.public_key)
    return {"status": "public key updated"}


@router.get("/partner-key")
async def get_partner_key(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve the chat partner's public key for E2E encryption.
    """
    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")

    repo = UserRepository(db)

    # Find the other user
    user_a = await repo.get_by_username(settings.USER_A_USERNAME)
    user_b = await repo.get_by_username(settings.USER_B_USERNAME)

    current_username = data["username"]
    partner = user_b if current_username == settings.USER_A_USERNAME else user_a

    if not partner or not partner.public_key:
        raise HTTPException(status_code=404, detail="Partner key not yet available")

    return {"public_key": partner.public_key, "username": partner.username}


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency to get authenticated user."""
    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    import uuid
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(data["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
