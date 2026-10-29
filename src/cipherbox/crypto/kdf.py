"""Argon2id key derivation for the vault master key.

Uses the maintained ``argon2-cffi`` library. All parameters are stored
in the vault config so the key can be re-derived on every unlock.
"""

from __future__ import annotations

from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw

KDF_ID = "argon2id"

# Resource limits for parsing attacker-controlled metadata. Argon2id is
# memory-hard, so absurd parameters are a denial-of-service vector.
MAX_MEMORY_COST = 1 << 30  # 1 GiB of kibibytes (i.e. ~1 TiB) is the hard cap
MAX_TIME_COST = 100
MAX_PARALLELISM = 64


@dataclass(frozen=True)
class KDFParams:
    """Argon2id parameters needed to derive the master key again."""

    time_cost: int
    memory_cost: int
    parallelism: int
    hash_len: int


def default_kdf_params() -> KDFParams:
    """Return parameters chosen for target-device performance.

    The values below follow current security guidance (OASP/CISA-style)
    for a single-user desktop CLI: enough memory and iterations to make
    brute-force expensive without making unlocking painful on a laptop.
    """
    return KDFParams(
        time_cost=3,
        memory_cost=65536,  # 64 MiB
        parallelism=4,
        hash_len=32,
    )


def derive_key(password: str, salt: bytes, params: KDFParams) -> bytes:
    """Derive a key of ``params.hash_len`` bytes from ``password`` and ``salt``.

    Argon2id with the given parameters. The salt must be cryptographically
    random and is stored in the vault config.
    """
    validate_kdf_params(params)
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost,
        parallelism=params.parallelism,
        hash_len=params.hash_len,
        type=Type.ID,
    )


def kdf_params_to_dict(params: KDFParams) -> dict:
    """Serialize KDF params to a JSON-friendly dict."""
    return {
        "time_cost": params.time_cost,
        "memory_cost": params.memory_cost,
        "parallelism": params.parallelism,
        "hash_len": params.hash_len,
    }


def kdf_params_from_dict(data: dict) -> KDFParams:
    """Deserialize KDF params from a JSON-friendly dict."""
    return KDFParams(
        time_cost=int(data["time_cost"]),
        memory_cost=int(data["memory_cost"]),
        parallelism=int(data["parallelism"]),
        hash_len=int(data["hash_len"]),
    )


def validate_kdf_params(params: KDFParams) -> None:
    """Reject resource limits that are too high (attacker-controlled metadata defense)."""
    if params.time_cost < 1 or params.time_cost > MAX_TIME_COST:
        raise ValueError(
            f"time_cost {params.time_cost} out of range [1, {MAX_TIME_COST}]"
        )
    if params.memory_cost < 8 or params.memory_cost > MAX_MEMORY_COST:
        raise ValueError(
            f"memory_cost {params.memory_cost} out of range [8, {MAX_MEMORY_COST}]"
        )
    if params.parallelism < 1 or params.parallelism > MAX_PARALLELISM:
        raise ValueError(
            f"parallelism {params.parallelism} out of range [1, {MAX_PARALLELISM}]"
        )
    if params.hash_len < 16 or params.hash_len > 64:
        raise ValueError(f"hash_len {params.hash_len} out of range [16, 64]")
