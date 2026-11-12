"""Server-side Ed25519 license issuance.

The private key is supplied only through the service environment or a private
key file.  It is never written to the repository, the database, logs, or HTTP
responses.  When no key is configured the control plane keeps working, but it
does not issue offline licenses; the desktop then falls back to online session
verification until the owner configures the key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("serpent.license_server")

LICENSE_ISSUER = "serpent-studio-control-plane"
LICENSE_AUDIENCE = "serpent-studio-desktop"
LICENSE_KEY_ID = "serpent-2026-1"
LICENSE_VERSION = 1
LICENSE_POLICY_VERSION = 1
LICENSE_TTL_SECONDS = 30 * 86400
DEVICE_LIMIT = 2
MAX_DEVICE_LIMIT = 100
HEARTBEAT_INTERVAL_SECONDS = 6 * 3600


def validate_device_limit(value: Any) -> int:
    """Reject coercions (including bool/float) for an administrator's quota."""
    if type(value) is not int or not 1 <= value <= MAX_DEVICE_LIMIT:
        raise ValueError(f"Kayıtlı cihaz sınırı 1–{MAX_DEVICE_LIMIT} arasında tam sayı olmalıdır.")
    return value


def validate_restricted_panels(value: Any) -> list[str]:
    """Preserve panel identifiers; never turn a malformed policy into full access."""
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(panel, str) or not panel.strip() for panel in value):
        raise ValueError("Restricted panels must be a list of nonempty strings.")
    return list(value)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


class LicenseSigner:
    """Load an Ed25519 private key and issue compact signed licenses."""

    def __init__(self, private_key=None, *, key_id: str = LICENSE_KEY_ID) -> None:
        self._private_key = private_key
        self.key_id = key_id
        self.public_key_b64 = ""
        if private_key is not None:
            try:
                from cryptography.hazmat.primitives import serialization

                raw_public = private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
                self.public_key_b64 = _b64url_encode(raw_public)
            except Exception:
                logger.exception("License public key could not be derived.")
                self._private_key = None

    @property
    def configured(self) -> bool:
        return self._private_key is not None

    @property
    def public_key_fingerprint(self) -> str:
        if not self.public_key_b64:
            return ""
        try:
            return hashlib.sha256(_b64url_decode(self.public_key_b64)).hexdigest()[:16]
        except Exception:
            return ""

    @classmethod
    def from_env(cls) -> "LicenseSigner":
        raw = os.environ.get("SERPENT_LICENSE_PRIVATE_KEY", "").strip()
        path = os.environ.get("SERPENT_LICENSE_PRIVATE_KEY_FILE", "").strip()
        if not raw and path:
            try:
                with open(os.path.expanduser(path), "r", encoding="utf-8") as stream:
                    raw = stream.read().strip()
            except OSError as exc:
                logger.warning("License key file could not be read (%s).", type(exc).__name__)
                raw = ""
        if not raw:
            return cls(None)
        private_key = cls._load_private_key(raw)
        if private_key is None:
            logger.error("SERPENT_LICENSE_PRIVATE_KEY is set but could not be parsed; licenses are disabled.")
            return cls(None)
        return cls(private_key)

    @staticmethod
    def _load_private_key(raw: str):
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError:
            logger.error("cryptography is not installed; license signing is disabled.")
            return None

        value = raw.strip()
        if "BEGIN" in value:
            try:
                key = serialization.load_pem_private_key(value.encode("utf-8"), password=None)
                if not isinstance(key, Ed25519PrivateKey):
                    logger.error("Configured license key is not an Ed25519 private key.")
                    return None
                return key
            except Exception as exc:
                logger.error("Configured PEM license key is invalid (%s).", type(exc).__name__)
                return None
        try:
            seed = _b64url_decode(value)
            if len(seed) != 32:
                # Also accept standard base64 (not only URL-safe base64).
                seed = base64.b64decode(value, validate=True)
            if len(seed) != 32:
                raise ValueError("expected 32 raw key bytes")
            return Ed25519PrivateKey.from_private_bytes(seed)
        except Exception as exc:
            logger.error("Configured license key is invalid (%s).", type(exc).__name__)
            return None

    def issue(
        self,
        *,
        username: str,
        role: str,
        display_name: str,
        device_fingerprint: str,
        device_limit: int = DEVICE_LIMIT,
        restricted_panels: Optional[list[str]] = None,
        account_expires_at: Optional[float] = None,
        ttl_seconds: int = LICENSE_TTL_SECONDS,
        now: Optional[float] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Return ``(compact_license, payload)`` or ``(None, None)`` when disabled."""
        if not self.configured or not device_fingerprint:
            return None, None
        issued_at = float(time.time() if now is None else now)
        if not math.isfinite(issued_at):
            raise ValueError("License issue time must be finite.")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)) or not math.isfinite(ttl_seconds):
            raise ValueError("License lifetime must be finite.")
        expires_at = issued_at + min(ttl_seconds, LICENSE_TTL_SECONDS)
        if account_expires_at is not None:
            if (isinstance(account_expires_at, bool)
                    or not isinstance(account_expires_at, (int, float))
                    or not math.isfinite(account_expires_at)):
                raise ValueError("Account expiry must be a finite timestamp or null.")
            expires_at = min(expires_at, account_expires_at)
        if expires_at <= issued_at:
            return None, None
        payload: Dict[str, Any] = {
            "iss": LICENSE_ISSUER,
            "aud": LICENSE_AUDIENCE,
            "ver": LICENSE_VERSION,
            "policy_version": LICENSE_POLICY_VERSION,
            "sub": str(username or "").strip().lower(),
            "role": str(role or "tester"),
            "name": str(display_name or ""),
            "device": str(device_fingerprint).strip().lower(),
            "seat_limit": validate_device_limit(device_limit),
            "restricted_panels": validate_restricted_panels(restricted_panels),
            "account_expires_at": account_expires_at,
            "iat": int(issued_at),
            "nbf": int(issued_at) - 60,
            "exp": expires_at,
            "jti": secrets.token_hex(16),
        }
        header = {"alg": "Ed25519", "typ": "SerpentLicense", "kid": self.key_id}
        header_part = _b64url_encode(
            json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        payload_part = _b64url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signing_input = (header_part + "." + payload_part).encode("ascii")
        try:
            signature = self._private_key.sign(signing_input)
        except Exception:
            logger.exception("License signing failed.")
            return None, None
        return header_part + "." + payload_part + "." + _b64url_encode(signature), payload


def public_key_fingerprint(public_key_b64: str) -> str:
    try:
        return hashlib.sha256(_b64url_decode(public_key_b64)).hexdigest()[:16]
    except Exception:
        return ""
