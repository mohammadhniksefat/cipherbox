"""Tests for the crypto primitives: Argon2id KDF and AES-GCM envelope."""

import base64

import pytest

from cipherbox.crypto.aead import (
    ALGORITHM_ID,
    ENVELOPE_FORMAT,
    DecryptionError,
    decrypt_envelope,
    encrypt_envelope,
)
from cipherbox.crypto.kdf import (
    KDF_ID,
    KDFParams,
    default_kdf_params,
    derive_key,
    kdf_params_from_dict,
    kdf_params_to_dict,
    validate_kdf_params,
)


def test_derive_key_returns_hash_len_bytes():
    key = derive_key(
        "correct horse battery staple", b"salt1234567890ab", default_kdf_params()
    )
    assert len(key) == 32


def test_derive_key_differs_with_different_salt():
    key1 = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    key2 = derive_key("pw", b"salt1234567890ac", default_kdf_params())
    assert key1 != key2


def test_encrypt_decrypt_round_trip():
    key = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    env = encrypt_envelope(b"plaintext", key, b"critical-aad")
    assert decrypt_envelope(env, key) == b"plaintext"


def test_decrypt_wrong_key_raises():
    key = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    wrong = derive_key("other", b"salt1234567890ab", default_kdf_params())
    env = encrypt_envelope(b"pt", key, b"aad")
    with pytest.raises(DecryptionError):
        decrypt_envelope(env, wrong)


def test_decrypt_tampered_ciphertext_raises():
    key = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    env = encrypt_envelope(b"pt", key, b"aad")
    ciphertext = bytearray(base64.b64decode(env["ciphertext"]))
    ciphertext[0] ^= 1  # flip a bit in the ciphertext
    env["ciphertext"] = base64.b64encode(bytes(ciphertext)).decode("ascii")
    with pytest.raises(DecryptionError):
        decrypt_envelope(env, key)


def test_decrypt_tampered_metadata_raises():
    key = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    env = encrypt_envelope(b"pt", key, b"critical-aad")
    env["format"] = "tampered-format"
    with pytest.raises(DecryptionError):
        decrypt_envelope(env, key)


def test_same_plaintext_different_ciphertext():
    key = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    env1 = encrypt_envelope(b"pt", key, b"aad")
    env2 = encrypt_envelope(b"pt", key, b"aad")
    assert env1["ciphertext"] != env2["ciphertext"]


def test_validate_kdf_params_rejects_extreme_memory():
    params = KDFParams(
        time_cost=1,
        memory_cost=2**32,
        parallelism=1,
        hash_len=32,
    )
    with pytest.raises(ValueError):
        validate_kdf_params(params)


def test_kdf_params_round_trip_dict():
    params = default_kdf_params()
    data = kdf_params_to_dict(params)
    assert kdf_params_from_dict(data) == params


def test_kdf_constants():
    assert KDF_ID == "argon2id"
    assert ALGORITHM_ID == "aes-256-gcm"
    assert ENVELOPE_FORMAT == "cipherbox-vault-enc/1"
