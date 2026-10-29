"""AES-GCM authenticated encryption envelopes for vault entry files.

Each envelope authenticates critical metadata as associated data (AAD),
so changing the format version, algorithm id, or schema version is
detected before any plaintext is ever produced. The caller-supplied AAD
is stored inside the envelope so ``decrypt_envelope(envelope, key)`` can
re-authenticate without re-supplying it.
"""

from __future__ import annotations

import base64
import hashlib
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ALGORITHM_ID = "aes-256-gcm"
ENVELOPE_FORMAT = "cipherbox-vault-enc/1"
NONCE_LEN = 12


class DecryptionError(Exception):
    """Raised when an envelope cannot be authenticated or decrypted.

    Fail closed: never return partial plaintext after an authentication
    failure.
    """


def _meta_digest(envelope: dict) -> bytes:
    """Digest of critical metadata: format, algorithm, schema version."""
    payload = (
        f"{envelope.get('format')}|{envelope.get('algorithm')}"
        f"|{envelope.get('schema_version')}"
    ).encode()
    return hashlib.sha256(payload).digest()


def _combined_aad(caller_aad_b64: str, envelope: dict) -> bytes:
    """Bind caller AAD together with the envelope's critical metadata."""
    payload = base64.b64decode(caller_aad_b64) + b"|" + _meta_digest(envelope)
    return hashlib.sha256(payload).digest()


def encrypt_envelope(plaintext: bytes, key: bytes, aad: bytes) -> dict:
    """Encrypt ``plaintext`` with AES-256-GCM under ``key``.

    Returns a dict with ``format``, ``algorithm``, ``schema_version``,
    ``nonce`` (base64), ``ciphertext`` (base64), and ``aad`` (base64).
    The caller-supplied ``aad`` is stored in the envelope and re-bound
    during decryption, so ``decrypt_envelope(envelope, key)`` is fully
    self-contained. A fresh random nonce is used every time, so identical
    plaintexts never produce identical ciphertexts under the same key.
    """
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(NONCE_LEN)  # 12 bytes, CSPRNG-backed
    envelope = {
        "format": ENVELOPE_FORMAT,
        "algorithm": ALGORITHM_ID,
        "schema_version": 1,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "aad": base64.b64encode(aad).decode("ascii"),
    }
    combined_aad = _combined_aad(envelope["aad"], envelope)
    ciphertext = aesgcm.encrypt(nonce, plaintext, combined_aad)
    envelope["ciphertext"] = base64.b64encode(ciphertext).decode("ascii")
    return envelope


def decrypt_envelope(envelope: dict, key: bytes) -> bytes:
    """Decrypt and authenticate an envelope produced by :func:`encrypt_envelope`.

    Fail closed: raises :class:`DecryptionError` on any authentication
    failure (wrong key, tampered ciphertext, tampered critical metadata)
    and never returns partial plaintext.
    """
    _check_format(envelope)
    aesgcm = AESGCM(key)
    nonce = base64.b64decode(envelope["nonce"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    combined_aad = _combined_aad(envelope["aad"], envelope)
    try:
        return aesgcm.decrypt(nonce, ciphertext, combined_aad)
    except InvalidTag as exc:
        raise DecryptionError("envelope authentication failed") from exc


def _check_format(envelope: dict) -> None:
    if not isinstance(envelope, dict):
        raise DecryptionError("envelope must be a JSON object")
    if envelope.get("format") != ENVELOPE_FORMAT:
        raise DecryptionError(f"unsupported envelope format {envelope.get('format')!r}")
    if envelope.get("algorithm") != ALGORITHM_ID:
        raise DecryptionError(f"unsupported algorithm {envelope.get('algorithm')!r}")
    for field in ("nonce", "ciphertext", "aad"):
        if field not in envelope:
            raise DecryptionError(f"envelope missing {field}")
