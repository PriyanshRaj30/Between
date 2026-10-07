"""
Private Chat controller — manages state, networking, and encryption
for the private messaging screen.
"""
import threading
import base64
import json
import os
import logging
from typing import Optional, Callable
from kivy.clock import Clock

from mobile.networking.api_client import APIClient
from mobile.networking.websocket_client import WebSocketClient
from mobile.security.encryption import encrypt_message, decrypt_message, b64_to_key
from mobile.security.authentication import AuthManager

logger = logging.getLogger(__name__)

# Default server URL (can be changed in config)
DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_WS_URL = "ws://localhost:8000/chat/ws"


class ChatController:
    """
    Manages:
    - Login flow
    - Message history loading
    - Real-time WebSocket messaging
    - E2E encryption/decryption
    - Partner online status
    """

    def __init__(
        self,
        on_message_received: Callable[[dict], None],
        on_partner_status: Callable[[bool], None],
        on_login_result: Callable[[bool, str], None],
    ):
        self._on_message_received = on_message_received
        self._on_partner_status = on_partner_status
        self._on_login_result = on_login_result

        self.auth = AuthManager()
        self.api = APIClient(DEFAULT_SERVER_URL)
        self._ws: Optional[WebSocketClient] = None
        self._enc_key: Optional[bytes] = None
        self._username: Optional[str] = None

        # Try to restore session
        if self.auth.is_logged_in():
            self._username = self.auth.username
            key_b64 = self.auth.encryption_key_b64
            if key_b64:
                self._enc_key = b64_to_key(key_b64)

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def is_logged_in(self) -> bool:
        return self.auth.is_logged_in()

    def login(self, username: str, password: str, encryption_passphrase: str) -> None:
        """
        Perform login in a background thread.
        Uses the encryption_passphrase to derive the shared AES key.
        """
        def _do_login():
            result = self.api.login(username, password)
            if not result:
                Clock.schedule_once(
                    lambda dt: self._on_login_result(False, "Login failed. Check credentials."), 0
                )
                return

            token = result["access_token"]
            self._username = username

            # Derive encryption key from shared passphrase
            from mobile.security.encryption import derive_key_from_password
            salt = b"texie-fixed-salt-v1"  # In production: exchange salt via server
            self._enc_key = derive_key_from_password(encryption_passphrase, salt)
            key_b64 = base64.b64encode(self._enc_key).decode()

            # Persist credentials
            self.auth.save(token, username, key_b64)

            Clock.schedule_once(
                lambda dt: self._on_login_result(True, f"Welcome, {username}!"), 0
            )

            # Start WebSocket connection
            self._start_ws(token)

        threading.Thread(target=_do_login, daemon=True).start()

    def connect_ws(self) -> None:
        """Connect WebSocket using stored token."""
        if self.auth.token and not self._ws:
            self._start_ws(self.auth.token)

    def _start_ws(self, token: str) -> None:
        self._ws = WebSocketClient(
            ws_url=DEFAULT_WS_URL,
            token=token,
            on_message=self._handle_ws_message,
            on_status_change=self._handle_ws_status,
            on_auth_error=self._handle_auth_error,
        )
        self._ws.start()

    def _handle_ws_message(self, data: dict) -> None:
        """Handle incoming WebSocket messages."""
        msg_type = data.get("type")

        if msg_type in ("message", "message_sent"):
            # Decrypt the message
            try:
                if self._enc_key:
                    plaintext = decrypt_message(
                        data["encrypted_content"],
                        data["iv"],
                        self._enc_key,
                    )
                else:
                    plaintext = "[encrypted — key not set]"
            except Exception as e:
                logger.warning(f"Decryption error: {e}")
                plaintext = "[decryption failed]"

            display_msg = {
                "id": data.get("id"),
                "sender_username": data.get("sender_username", ""),
                "text": plaintext,
                "created_at": data.get("created_at"),
                "is_mine": data.get("sender_username") == self._username or msg_type == "message_sent",
            }
            Clock.schedule_once(lambda dt: self._on_message_received(display_msg), 0)

        elif msg_type == "status":
            online = data.get("online", False)
            Clock.schedule_once(lambda dt: self._on_partner_status(online), 0)

        elif msg_type == "read_receipt":
            pass  # Could update UI with read ticks

    def _handle_ws_status(self, connected: bool) -> None:
        if not connected:
            Clock.schedule_once(lambda dt: self._on_partner_status(False), 0)

    def _handle_auth_error(self) -> None:
        """
        Called when WS gets 403/401 — token is expired or invalid.
        Clear stored credentials so the login screen re-appears.
        """
        logger.warning("[CONTROLLER] Auth error from WS — clearing session, re-prompting login")
        self.auth.clear()
        self._ws = None
        self._enc_key = None
        self._username = None
        Clock.schedule_once(
            lambda dt: self._on_login_result(
                False,
                "Session expired — please log in again."
            ), 0
        )

    def send_message(self, text: str) -> bool:
        """
        Encrypt and send a message.
        Returns False if not connected or key not set.
        """
        if not self._ws or not self._enc_key:
            return False

        text = text.strip()
        if not text:
            return False

        try:
            encrypted_content, iv = encrypt_message(text, self._enc_key)
            self._ws.send_message(encrypted_content, iv)
            return True
        except Exception as e:
            logger.error(f"Encryption/send failed: {e}")
            return False

    def load_history(self, callback: Callable[[list], None]) -> None:
        """Load message history from server in background."""
        def _fetch():
            token = self.auth.token
            if not token:
                Clock.schedule_once(lambda dt: callback([]), 0)
                return

            result = self.api.get_history(token, limit=50)
            messages = []
            if result:
                for msg in result.get("messages", []):
                    try:
                        if self._enc_key:
                            text = decrypt_message(
                                msg["encrypted_content"], msg["iv"], self._enc_key
                            )
                        else:
                            text = "[key not set]"
                    except Exception:
                        text = "[decryption error]"

                    messages.append({
                        "id": msg["id"],
                        "sender_id": msg.get("sender_id"),
                        "text": text,
                        "created_at": msg.get("created_at"),
                        "is_mine": msg.get("sender_id") == self._get_my_id(),
                    })

            Clock.schedule_once(lambda dt: callback(messages), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _get_my_id(self) -> Optional[str]:
        # For history display, compare sender_username stored locally
        return None  # Simplified: we use sender_username in WS path

    def disconnect(self) -> None:
        if self._ws:
            self._ws.stop()
            self._ws = None

