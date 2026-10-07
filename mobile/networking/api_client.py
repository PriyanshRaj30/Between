"""
REST API client for Texie backend communication.
Handles login, fetching message history, and public key exchange.
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional


class APIClient:
    """
    Lightweight HTTP client using Python's stdlib urllib.
    Avoids heavy dependencies for the mobile app.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def login(self, username: str, password: str) -> Optional[dict]:
        """
        Authenticate and receive JWT token.
        Returns: {"access_token": ..., "username": ...} or None on failure.
        """
        url = f"{self.base_url}/auth/token"
        data = urllib.parse.urlencode({
            "username": username,
            "password": password,
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"[API] Login failed: {e.code}")
            return None
        except Exception as e:
            print(f"[API] Login error: {e}")
            return None

    def get_history(self, token: str, limit: int = 50) -> Optional[dict]:
        """Fetch conversation history."""
        url = f"{self.base_url}/chat/history?token={token}&limit={limit}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[API] History error: {e}")
            return None

    def upload_public_key(self, token: str, public_key_pem: str) -> bool:
        """Upload our public key for E2E key exchange."""
        url = f"{self.base_url}/auth/public-key"
        data = json.dumps({"public_key": public_key_pem}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[API] Public key upload error: {e}")
            return False

    def get_partner_key(self, token: str) -> Optional[str]:
        """Get partner's public key for E2E encryption."""
        url = f"{self.base_url}/auth/partner-key"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("public_key")
        except Exception as e:
            print(f"[API] Partner key error: {e}")
            return None

    def health_check(self) -> bool:
        """Check if backend is reachable."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/health", timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
