"""
WebSocket client for real-time messaging.
Runs in a background thread to avoid blocking the Kivy UI thread.
Automatically reconnects on disconnect.
"""
import json
import threading
import time
import logging
from typing import Optional, Callable
import websocket  # websocket-client library

logger = logging.getLogger(__name__)

# Reconnect settings
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY_SECONDS = 3


class WebSocketClient:
    """
    WebSocket client that:
    - Runs in a background thread
    - Delivers received messages via callback
    - Handles reconnection automatically
    - Queues messages while offline
    """

    def __init__(
        self,
        ws_url: str,
        token: str,
        on_message: Callable[[dict], None],
        on_status_change: Optional[Callable[[bool], None]] = None,
        on_auth_error: Optional[Callable[[], None]] = None,
    ):
        self.ws_url = ws_url
        self.token = token
        self._on_message = on_message
        self._on_status_change = on_status_change
        self._on_auth_error = on_auth_error

        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._connected = False
        self._reconnect_count = 0
        self._auth_failed = False   # Set to True on 403 — stops retry loop

        # Offline message queue
        self._pending_messages: list[dict] = []
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        """Start the WebSocket connection in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Gracefully disconnect."""
        self._running = False
        if self._ws:
            self._ws.close()

    def send_message(self, encrypted_content: str, iv: str) -> None:
        """
        Send an encrypted message. If offline, queues it for later delivery.
        """
        payload = {
            "type": "message",
            "encrypted_content": encrypted_content,
            "iv": iv,
        }
        if self._connected and self._ws:
            try:
                self._ws.send(json.dumps(payload))
            except Exception as e:
                logger.warning(f"[WS] Send failed, queuing: {e}")
                with self._lock:
                    self._pending_messages.append(payload)
        else:
            with self._lock:
                self._pending_messages.append(payload)

    def send_read_receipt(self, message_id: str) -> None:
        """Notify partner that a message has been read."""
        if self._connected and self._ws:
            try:
                self._ws.send(json.dumps({"type": "read", "message_id": message_id}))
            except Exception:
                pass

    def _flush_pending(self) -> None:
        """Send any queued messages after reconnection."""
        with self._lock:
            pending = self._pending_messages[:]
            self._pending_messages.clear()
        for msg in pending:
            try:
                self._ws.send(json.dumps(msg))
                logger.info(f"[WS] Flushed queued message")
            except Exception as e:
                logger.warning(f"[WS] Flush failed: {e}")

    def _run_loop(self) -> None:
        """Main reconnection loop."""
        while self._running and self._reconnect_count < MAX_RECONNECT_ATTEMPTS:
            # Stop immediately if we got a 403 — retrying won't help
            if self._auth_failed:
                break

            url = f"{self.ws_url}?token={self.token}"
            logger.info(f"[WS] Connecting to {self.ws_url}...")

            self._ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_ws_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self._ws.run_forever(ping_interval=30, ping_timeout=10)

            if not self._running or self._auth_failed:
                break

            self._reconnect_count += 1
            wait = min(RECONNECT_DELAY_SECONDS * self._reconnect_count, 30)
            logger.info(f"[WS] Reconnecting in {wait}s (attempt {self._reconnect_count})")
            time.sleep(wait)

    def _on_open(self, ws) -> None:
        self._connected = True
        self._reconnect_count = 0
        logger.info("[WS] Connected")
        if self._on_status_change:
            self._on_status_change(True)
        # Flush any offline-queued messages
        self._flush_pending()

    def _on_ws_message(self, ws, raw: str) -> None:
        try:
            data = json.loads(raw)
            self._on_message(data)
        except Exception as e:
            logger.warning(f"[WS] Bad message: {e}")

    def _on_error(self, ws, error) -> None:
        error_str = str(error)
        logger.warning(f"[WS] Error: {error_str}")
        # 403 = invalid/expired token — stop retrying and trigger re-login
        if "403" in error_str or "Forbidden" in error_str or "401" in error_str:
            logger.warning("[WS] Auth error (403/401) — stopping reconnect, clearing session")
            self._auth_failed = True
            self._running = False
            if self._on_auth_error:
                self._on_auth_error()

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        self._connected = False
        logger.info(f"[WS] Closed: {close_status_code} {close_msg}")
        if self._on_status_change:
            self._on_status_change(False)
