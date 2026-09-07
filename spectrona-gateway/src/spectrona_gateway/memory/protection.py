"""Storage protection for memory content.

The public memory API returns redacted content. This module keeps the
persistence layer aligned with that behavior by making raw storage opt-in.
"""

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .. import config
from ..dlp import redact_text


VALID_RAW_STORAGE_MODES = {"redacted", "encrypted", "plaintext"}
_ENVELOPE_PREFIX = "spectrona:v1"
_AUTH_CONTEXT = b"spectrona-memory-v1"


@dataclass(frozen=True)
class ContentStorage:
    content: str
    redacted_content: str
    encrypted_content: Optional[str]
    raw_storage_mode: str
    raw_storage_reason: str
    raw_content_stored: bool
    encrypted_content_stored: bool


def prepare_content_storage(content: str, requested_mode: Optional[str] = None) -> ContentStorage:
    raw_content = str(content or "")
    redacted_content = redact_text(raw_content)
    mode = _normalize_mode(requested_mode or config.MEMORY_RAW_STORAGE)

    if mode == "plaintext":
        if not config.MEMORY_ALLOW_PLAINTEXT:
            return ContentStorage(
                content=redacted_content,
                redacted_content=redacted_content,
                encrypted_content=None,
                raw_storage_mode="redacted",
                raw_storage_reason="plaintext_requires_explicit_policy",
                raw_content_stored=False,
                encrypted_content_stored=False,
            )
        return ContentStorage(
            content=raw_content,
            redacted_content=redacted_content,
            encrypted_content=None,
            raw_storage_mode="plaintext",
            raw_storage_reason="plaintext_allowed_by_policy",
            raw_content_stored=True,
            encrypted_content_stored=False,
        )

    if mode == "encrypted":
        encrypted = encrypt_text(raw_content)
        return ContentStorage(
            content=redacted_content,
            redacted_content=redacted_content,
            encrypted_content=encrypted,
            raw_storage_mode="encrypted",
            raw_storage_reason="encrypted_raw_content",
            raw_content_stored=False,
            encrypted_content_stored=True,
        )

    return ContentStorage(
        content=redacted_content,
        redacted_content=redacted_content,
        encrypted_content=None,
        raw_storage_mode="redacted",
        raw_storage_reason="redacted_by_default",
        raw_content_stored=False,
        encrypted_content_stored=False,
    )


def storage_metadata(row: dict) -> dict:
    mode = str(row.get("raw_storage_mode") or "legacy_plaintext")
    reason = str(row.get("raw_storage_reason") or "legacy_plaintext_existing_row")
    encrypted_content = row.get("encrypted_content")
    return {
        "raw_storage_mode": mode,
        "raw_storage_reason": reason,
        "raw_content_stored": mode in {"plaintext", "legacy_plaintext"},
        "encrypted_content_stored": bool(encrypted_content),
    }


def redaction_was_applied(safe_content: str, stored_content: str) -> bool:
    return safe_content != stored_content or "[REDACTED_" in safe_content


def encrypt_text(plaintext: str) -> str:
    key = _memory_key()
    nonce = os.urandom(16)
    payload = str(plaintext or "").encode("utf-8")
    ciphertext = _xor_stream(payload, key, nonce)
    tag = hmac.new(key, _AUTH_CONTEXT + nonce + ciphertext, hashlib.sha256).digest()
    return ":".join([
        _ENVELOPE_PREFIX,
        _b64(nonce),
        _b64(ciphertext),
        _b64(tag),
    ])


def decrypt_text(envelope: str) -> str:
    parts = str(envelope or "").split(":")
    if len(parts) != 5 or ":".join(parts[:2]) != _ENVELOPE_PREFIX:
        raise ValueError("invalid memory encryption envelope")
    nonce = _unb64(parts[2])
    ciphertext = _unb64(parts[3])
    tag = _unb64(parts[4])
    key = _memory_key()
    expected = hmac.new(key, _AUTH_CONTEXT + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise ValueError("invalid memory encryption tag")
    return _xor_stream(ciphertext, key, nonce).decode("utf-8")


def _normalize_mode(value: str) -> str:
    mode = str(value or "redacted").strip().lower()
    return mode if mode in VALID_RAW_STORAGE_MODES else "redacted"


def _memory_key() -> bytes:
    explicit = os.getenv("SPECTRONA_MEMORY_ENCRYPTION_KEY")
    if explicit:
        return hashlib.sha256(explicit.encode("utf-8")).digest()

    path = Path(config.MEMORY_ENCRYPTION_KEY_PATH).expanduser()
    if path.exists():
        raw = path.read_text().strip()
        try:
            decoded = _unb64(raw)
            if len(decoded) >= 32:
                return hashlib.sha256(decoded).digest()
        except Exception:
            pass
        return hashlib.sha256(raw.encode("utf-8")).digest()

    key = os.urandom(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_b64(key) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return hashlib.sha256(key).digest()


def _xor_stream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(data):
        counter_bytes = counter.to_bytes(8, "big")
        output.extend(hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return bytes(left ^ right for left, right in zip(data, output))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))
