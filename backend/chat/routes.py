"""
Chat routes: WebSocket endpoint + conversation history REST endpoint.
"""
import json
import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.database.session import get_db, AsyncSessionLocal
from backend.database.repository import UserRepository
from backend.auth.authentication import decode_token
from backend.chat.websocket import manager
from backend.chat.message_service import MessageService
from backend.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.get("/history")
async def get_history(
    limit: int = Query(default=50, le=200),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch recent conversation history.
    Returns encrypted messages — client decrypts them.
    """
    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")

    service = MessageService(db)
    messages = await service.get_conversation_history(limit=limit)

    serialized = [service.serialize_message(m, data["username"]) for m in messages]
    return {
        "messages": serialized,
        "conversation_id": settings.CONVERSATION_ID,
    }


@router.get("/status")
async def get_status(token: str = Query(...)):
    """Check who is currently online."""
    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "online_count": manager.online_count(),
        "partner_online": manager.is_online(
            settings.USER_B_USERNAME
            if data["username"] == settings.USER_A_USERNAME
            else settings.USER_A_USERNAME
        ),
    }


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time messaging.

    Protocol:
    - Client connects with ?token=<jwt>
    - Server authenticates from token
    - Client sends: {"type": "message", "encrypted_content": "...", "iv": "..."}
    - Server stores & forwards to partner
    - Server sends: {"type": "message", ...message_data...}
    - Client sends: {"type": "read", "message_id": "..."}
    - Server sends: {"type": "status", "user": "...", "online": true/false}
    """
    # Authenticate from query parameter
    data = decode_token(token)
    if not data:
        await websocket.close(code=1008, reason="Invalid token")
        return

    username = data["username"]
    user_id = uuid.UUID(data["sub"])

    await manager.connect(websocket, username)

    # Determine partner username
    partner_username = (
        settings.USER_B_USERNAME
        if username == settings.USER_A_USERNAME
        else settings.USER_A_USERNAME
    )

    # Notify partner that this user came online
    await manager.send_to(partner_username, {
        "type": "status",
        "user": username,
        "online": True,
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = payload.get("type")

            if msg_type == "message":
                # Validate required fields
                encrypted_content = payload.get("encrypted_content")
                iv = payload.get("iv")

                if not encrypted_content or not iv:
                    await websocket.send_json({"type": "error", "detail": "Missing encrypted_content or iv"})
                    continue

                # Store encrypted message in DB
                async with AsyncSessionLocal() as db:
                    service = MessageService(db)
                    stored = await service.store_message(
                        sender_id=user_id,
                        encrypted_content=encrypted_content,
                        iv=iv,
                    )
                    serialized = service.serialize_message(stored, username)
                    # Add sender username for UI purposes
                    serialized["sender_username"] = username

                # Echo back to sender (confirmation)
                await websocket.send_json({"type": "message_sent", **serialized})

                # Deliver to partner
                delivered = await manager.send_to(partner_username, {
                    "type": "message",
                    **serialized,
                })

                if not delivered:
                    # Partner is offline — message is stored; they'll fetch on next login
                    logger.info(f"[WS] Partner {partner_username} offline, message queued in DB")

            elif msg_type == "read":
                message_id = payload.get("message_id")
                if message_id:
                    async with AsyncSessionLocal() as db:
                        service = MessageService(db)
                        await service.mark_read(uuid.UUID(message_id))
                    await manager.send_to(partner_username, {
                        "type": "read_receipt",
                        "message_id": message_id,
                        "reader": username,
                    })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"[WS] {username} disconnected")
    finally:
        manager.disconnect(username)
        # Update DB
        async with AsyncSessionLocal() as db:
            repo = UserRepository(db)
            await repo.set_offline(user_id)

        # Notify partner of offline status
        await manager.send_to(partner_username, {
            "type": "status",
            "user": username,
            "online": False,
        })
