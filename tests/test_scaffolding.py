"""Tests for project scaffolding: packaging, entry point, and error types."""

from cipherbox import errors


def test_errors_module_exports_expected_types():
    assert hasattr(errors, "VaultError")
    assert hasattr(errors, "DuplicateIdError")
    assert hasattr(errors, "InvalidEntryError")
    assert hasattr(errors, "MissingEntryError")
    assert hasattr(errors, "MalformedFileError")
    assert hasattr(errors, "ConfirmationRequiredError")


def test_exit_code_constants_exist():
    assert errors.EXIT_OK == 0
    assert errors.EXIT_ERROR == 1
    assert errors.EXIT_VALIDATION == 2
    assert errors.EXIT_NOT_FOUND == 3
    assert errors.EXIT_DUPLICATE == 4
    assert errors.EXIT_CONFIRMATION == 5


def test_error_types_are_subclasses_of_vault_error():
    assert issubclass(errors.DuplicateIdError, errors.VaultError)
    assert issubclass(errors.InvalidEntryError, errors.VaultError)
    assert issubclass(errors.MissingEntryError, errors.VaultError)
    assert issubclass(errors.MalformedFileError, errors.VaultError)
    assert issubclass(errors.ConfirmationRequiredError, errors.VaultError)
