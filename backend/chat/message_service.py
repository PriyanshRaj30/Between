"""
Message service: validates, stores, and routes encrypted messages.
The server NEVER touches plaintext — it only stores and forwards ciphertext.
"""
import logging
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.repository import MessageRepository, UserRepository
from backend.database.models import Message
from backend.config import settings

logger = logging.getLogger(__name__)


class MessageService:
    """
    Business logic for message handling.
    All content is treated as opaque encrypted bytes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.msg_repo = MessageRepository(db)
        self.user_repo = UserRepository(db)

    async def store_message(
        self,
        sender_id: UUID,
        encrypted_content: str,
        iv: str,
    ) -> Message:
        """
        Store an encrypted message. Returns the saved message.
        The encrypted_content and iv are stored as-is.
        """
        msg = await self.msg_repo.create(
            conversation_id=settings.CONVERSATION_ID,
            sender_id=sender_id,
            encrypted_content=encrypted_content,
            iv=iv,
        )
        logger.info(f"[MSG] Stored message {msg.id} from {sender_id}")
        return msg

    async def get_conversation_history(self, limit: int = 50) -> list[Message]:
        """Retrieve last N messages for the conversation."""
        return await self.msg_repo.get_recent(
            conversation_id=settings.CONVERSATION_ID,
            limit=limit,
        )

    async def mark_delivered(self, message_id: UUID) -> None:
        await self.msg_repo.mark_delivered(message_id)

    async def mark_read(self, message_id: UUID) -> None:
        await self.msg_repo.mark_read(message_id)

    def serialize_message(self, msg: Message, current_username: str) -> dict:
        """Serialize a message to dict for WebSocket/REST delivery."""
        return {
            "id": str(msg.id),
            "conversation_id": msg.conversation_id,
            "sender_id": str(msg.sender_id),
            "encrypted_content": msg.encrypted_content,
            "iv": msg.iv,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
        }
