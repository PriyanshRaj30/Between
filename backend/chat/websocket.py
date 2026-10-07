"""
WebSocket connection manager.
Maintains exactly two connections for the private conversation.
"""
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for the two-person chat.
    Stores connections keyed by username.
    """

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str) -> None:
        await websocket.accept()
        self._connections[username] = websocket
        logger.info(f"[WS] {username} connected. Online: {list(self._connections.keys())}")

    def disconnect(self, username: str) -> None:
        self._connections.pop(username, None)
        logger.info(f"[WS] {username} disconnected. Online: {list(self._connections.keys())}")

    async def send_to(self, username: str, message: dict) -> bool:
        """Send a message to a specific user. Returns True if delivered."""
        ws = self._connections.get(username)
        if ws:
            try:
                await ws.send_json(message)
                return True
            except Exception as e:
                logger.warning(f"[WS] Failed to send to {username}: {e}")
                self.disconnect(username)
        return False

    async def broadcast(self, message: dict, exclude: Optional[str] = None) -> None:
        """Send to all connected users, optionally excluding one."""
        for username, ws in list(self._connections.items()):
            if username == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"[WS] Broadcast failed for {username}: {e}")
                self.disconnect(username)

    def is_online(self, username: str) -> bool:
        return username in self._connections

    def online_count(self) -> int:
        return len(self._connections)


# Singleton manager shared across the app
manager = ConnectionManager()
