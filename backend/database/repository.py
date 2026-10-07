"""
Database repository — all DB operations live here.
"""
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.database.models import User, Message


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_public_key(self, user_id: UUID, public_key: str) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(public_key=public_key)
        )

    async def update_last_seen(self, user_id: UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_seen=datetime.utcnow(), is_online=True)
        )

    async def set_offline(self, user_id: UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_online=False)
        )

    async def create(self, username: str, hashed_password: str) -> User:
        user = User(username=username, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        conversation_id: str,
        sender_id: UUID,
        encrypted_content: str,
        iv: str,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            encrypted_content=encrypted_content,
            iv=iv,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def get_recent(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))

    async def mark_delivered(self, message_id: UUID) -> None:
        await self.db.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(delivered_at=datetime.utcnow())
        )

    async def mark_read(self, message_id: UUID) -> None:
        await self.db.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(read_at=datetime.utcnow())
        )
