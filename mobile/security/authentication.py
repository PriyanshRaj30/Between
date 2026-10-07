"""
Authentication manager for the mobile client.
Handles token storage and refresh.
"""
import json
import os
from typing import Optional

# Secure local storage path
_CREDENTIALS_FILE = os.path.join(
    os.path.expanduser("~"), ".texie", "credentials.json"
)


class AuthManager:
    """
    Manages local credential storage and token lifecycle.
    Credentials are stored in a local JSON file (would use keychain on mobile).
    """

    def __init__(self):
        self._token: Optional[str] = None
        self._username: Optional[str] = None
        self._load()

    def save(self, token: str, username: str, encryption_key_b64: str) -> None:
        """Persist credentials locally."""
        self._token = token
        self._username = username
        os.makedirs(os.path.dirname(_CREDENTIALS_FILE), exist_ok=True)
        with open(_CREDENTIALS_FILE, "w") as f:
            json.dump({
                "token": token,
                "username": username,
                "encryption_key": encryption_key_b64,
            }, f)

    def _load(self) -> None:
        """Load credentials from local storage."""
        if os.path.exists(_CREDENTIALS_FILE):
            try:
                with open(_CREDENTIALS_FILE) as f:
                    data = json.load(f)
                self._token = data.get("token")
                self._username = data.get("username")
                self._encryption_key_b64 = data.get("encryption_key")
            except Exception:
                pass

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def encryption_key_b64(self) -> Optional[str]:
        return getattr(self, "_encryption_key_b64", None)

    def clear(self) -> None:
        """Log out — remove stored credentials."""
        self._token = None
        self._username = None
        if os.path.exists(_CREDENTIALS_FILE):
            os.remove(_CREDENTIALS_FILE)

    def is_logged_in(self) -> bool:
        return bool(self._token and self._username)
