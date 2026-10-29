"""Error types and exit codes for the cipherbox vault application."""

from __future__ import annotations

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_VALIDATION = 2
EXIT_NOT_FOUND = 3
EXIT_DUPLICATE = 4
EXIT_CONFIRMATION = 5


class VaultError(Exception):
    """Base exception for all vault errors."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class DuplicateIdError(VaultError):
    """Raised when an entry ID already exists in the vault."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_DUPLICATE)


class InvalidEntryError(VaultError):
    """Raised when an entry fails schema validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_VALIDATION)


class MissingEntryError(VaultError):
    """Raised when an entry is not found in the vault."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_NOT_FOUND)


class MalformedFileError(VaultError):
    """Raised when a vault entry file is malformed or unreadable."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_VALIDATION)


class DecryptionError(VaultError):
    """Raised when an encrypted entry cannot be authenticated or decrypted.

    Fail closed: authentication failures must not produce partial plaintext.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_VALIDATION)


class ConfirmationRequiredError(VaultError):
    """Raised when a destructive operation requires confirmation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_CONFIRMATION)


class ConflictError(VaultError):
    """Raised when two entry files resolve to the same stable entry ID.

    Never silently picked between: both conflicting files are preserved
    for manual recovery.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_ERROR)
