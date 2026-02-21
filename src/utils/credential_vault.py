"""Encrypted exchange credential persistence helpers (step 38)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Mapping


class CredentialVaultError(RuntimeError):
    """Raised when encrypted credential storage fails."""


def persist_exchange_credentials(
    config: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    """Persist exchange API credentials to an encrypted local vault.

    Behavior:
    - If both `exchange.api_key` and `exchange.api_secret` are empty, no file is written.
    - If either key exists, `CONFIG_MASTER_KEY` is required for encryption.
    """
    exchange = config.get("exchange")
    if not isinstance(exchange, Mapping):
        return None

    api_key = _read_str(exchange.get("api_key"))
    api_secret = _read_str(exchange.get("api_secret"))
    if not api_key and not api_secret:
        return None

    env_mapping = env or os.environ
    master_key = _read_str(env_mapping.get("CONFIG_MASTER_KEY"))
    if not master_key:
        raise CredentialVaultError("CONFIG_MASTER_KEY is required when exchange API credentials are provided")

    payload = {
        "version": 1,
        "updated_at_ms": int(time.time() * 1000),
        "api_key": _encrypt_text(api_key, master_key),
        "api_secret": _encrypt_text(api_secret, master_key),
    }

    vault_path = credential_vault_path(config)
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return vault_path


def read_exchange_credentials(
    config: Mapping[str, Any],
    *,
    master_key: str,
) -> dict[str, str]:
    """Read and decrypt API credentials from vault file."""
    vault_path = credential_vault_path(config)
    if not vault_path.exists():
        raise CredentialVaultError(f"credential vault not found: {vault_path}")

    try:
        payload = json.loads(vault_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialVaultError(f"invalid credential vault: {vault_path}") from exc

    if not isinstance(payload, Mapping):
        raise CredentialVaultError("invalid credential payload")

    return {
        "api_key": _decrypt_text(_require_mapping(payload, "api_key"), master_key),
        "api_secret": _decrypt_text(_require_mapping(payload, "api_secret"), master_key),
    }


def credential_vault_path(config: Mapping[str, Any]) -> Path:
    """Build vault path under `system.data_dir/secure`."""
    system = config.get("system")
    if not isinstance(system, Mapping):
        raise CredentialVaultError("config.system is required for credential vault")

    data_dir = _read_str(system.get("data_dir"))
    if not data_dir:
        raise CredentialVaultError("config.system.data_dir is required for credential vault")

    return Path(data_dir).expanduser() / "secure" / "exchange_credentials.enc.json"


def _encrypt_text(plaintext: str, master_key: str) -> dict[str, str]:
    raw = plaintext.encode("utf-8")
    nonce = secrets.token_bytes(16)
    encryption_key = _derive_key(master_key.encode("utf-8"), nonce, b"enc")
    mac_key = _derive_key(master_key.encode("utf-8"), nonce, b"mac")
    ciphertext = _xor_stream(raw, encryption_key)
    signature = hmac.new(mac_key, ciphertext, hashlib.sha256).digest()

    return {
        "nonce": _b64e(nonce),
        "ciphertext": _b64e(ciphertext),
        "mac": _b64e(signature),
    }


def _decrypt_text(payload: Mapping[str, Any], master_key: str) -> str:
    nonce = _b64d(_read_str(payload.get("nonce")))
    ciphertext = _b64d(_read_str(payload.get("ciphertext")))
    signature = _b64d(_read_str(payload.get("mac")))

    encryption_key = _derive_key(master_key.encode("utf-8"), nonce, b"enc")
    mac_key = _derive_key(master_key.encode("utf-8"), nonce, b"mac")
    expected = hmac.new(mac_key, ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise CredentialVaultError("credential vault integrity check failed")

    plaintext = _xor_stream(ciphertext, encryption_key)
    return plaintext.decode("utf-8")


def _derive_key(master: bytes, nonce: bytes, purpose: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", master + purpose, nonce, 120_000, dklen=32)


def _xor_stream(data: bytes, key: bytes) -> bytes:
    if not data:
        return b""

    output = bytearray()
    counter = 0
    while len(output) < len(data):
        counter_bytes = counter.to_bytes(8, "big")
        output.extend(hashlib.sha256(key + counter_bytes).digest())
        counter += 1
    return bytes(d ^ k for d, k in zip(data, output[: len(data)]))


def _read_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise CredentialVaultError(f"missing encrypted field: {key}")
    return value


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    try:
        return base64.b64decode(data.encode("ascii"), validate=True)
    except Exception as exc:
        raise CredentialVaultError("invalid base64 payload in credential vault") from exc
