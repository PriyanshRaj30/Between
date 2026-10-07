"""
Client-side E2E encryption using AES-256-GCM.

All encryption/decryption happens on the device.
The server only ever sees ciphertext.

Key derivation: Both users derive the same shared AES key
using Diffie-Hellman key exchange (ECDH with X25519).

For simplicity in MVP, we use a pre-shared symmetric key
stored securely on the device. Full ECDH can be layered in Phase 4.
"""
import os
import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption
)


# ── Symmetric key management ──────────────────────────────────────────────────

def generate_aes_key() -> bytes:
    """Generate a random 256-bit AES key."""
    return os.urandom(32)


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit key from a password using scrypt.
    Useful for generating the shared key from a passphrase agreed out-of-band.
    """
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=2**14,
        r=8,
        p=1,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))


# ── AES-GCM Encryption ────────────────────────────────────────────────────────

def encrypt_message(plaintext: str, key: bytes) -> tuple[str, str]:
    """
    Encrypt a plaintext message using AES-256-GCM.

    Returns:
        (encrypted_content_b64, iv_b64) — both base64-encoded strings
        suitable for JSON transport.
    """
    iv = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    return (
        base64.b64encode(ciphertext).decode("utf-8"),
        base64.b64encode(iv).decode("utf-8"),
    )


def decrypt_message(encrypted_content_b64: str, iv_b64: str, key: bytes) -> str:
    """
    Decrypt a message received from the server.

    Returns:
        Decrypted plaintext string.

    Raises:
        ValueError if decryption fails (wrong key or tampered data).
    """
    try:
        ciphertext = base64.b64decode(encrypted_content_b64)
        iv = base64.b64decode(iv_b64)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


# ── ECDH Key Pair (for future full E2E) ──────────────────────────────────────

def generate_x25519_keypair() -> tuple[bytes, bytes]:
    """
    Generate an X25519 key pair.
    Returns (private_key_bytes, public_key_bytes).
    """
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    )
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private_bytes, public_bytes


def derive_shared_secret(my_private_bytes: bytes, their_public_bytes: bytes) -> bytes:
    """
    Perform ECDH key exchange to derive a shared secret.
    Both parties independently compute the same secret.
    """
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
    private_key = X25519PrivateKey.from_private_bytes(my_private_bytes)
    their_public = X25519PublicKey.from_public_bytes(their_public_bytes)
    shared = private_key.exchange(their_public)
    # Hash the raw secret to get a proper AES key
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"texie-e2e-key",
        backend=default_backend(),
    )
    return hkdf.derive(shared)


# ── Key Storage Helpers ───────────────────────────────────────────────────────

def key_to_b64(key: bytes) -> str:
    return base64.b64encode(key).decode("utf-8")


def b64_to_key(b64: str) -> bytes:
    return base64.b64decode(b64)
