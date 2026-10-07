"""
Database models for Texie.
Only stores encrypted message content — never plaintext.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
import uuid


class Base(DeclarativeBase):
    pass


class User(Base):
    """
    Exactly two users exist in the system.
    No public registration — only pre-seeded users.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    public_key = Column(Text, nullable=True)  # PEM-encoded public key for E2E
    device_fingerprint = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)
    is_online = Column(Boolean, default=False)

    messages_sent = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        lazy="dynamic",
    )


class Message(Base):
    """
    Messages are stored with ONLY encrypted_content.
    The server never sees plaintext.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String(64), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    encrypted_content = Column(Text, nullable=False)   # Ciphertext only
    iv = Column(String(256), nullable=True)            # Initialization vector for AES
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
