def _vault_meta(vault_dir, encrypted=True, salt=b"\x02" * 16, params=None):
    import base64
    import json

    from cipherbox.crypto.kdf import kdf_params_to_dict

    if params is None:
        from cipherbox.crypto.kdf import default_kdf_params

        params = default_kdf_params()
    meta = {
        "encrypted": encrypted,
        "kdf": "argon2id",
        "kdf_params": kdf_params_to_dict(params),
        "salt": base64.b64encode(salt).decode("ascii"),
    }
    (vault_dir / "config.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def test_unlock_uses_keyring_when_available(tmp_path, monkeypatch, capsys):
    from cipherbox.__main__ import main

    # Seed an encrypted vault with a known password-derived key.
    from cipherbox.crypto.kdf import default_kdf_params, derive_key
    from cipherbox.crypto.keyring import KeyringStore

    vault_dir = tmp_path / "my-vault"
    vault_dir.mkdir()
    entries_dir = vault_dir / "entries"
    entries_dir.mkdir()
    password = "master-pass"
    params = default_kdf_params()
    key = derive_key(password, b"\x02" * 16, params)
    _vault_meta(vault_dir, salt=b"\x02" * 16, params=params)

    # Pre-populate keyring with the derived key.
    store = KeyringStore(service_name="test-cipherbox")
    monkeypatch.setattr(
        "cipherbox.crypto.keyring._keyring_mod", store
    )  # placeholder, replaced below

    class FakeKeyring:
        def __init__(self):
            self._data = {}

        def get_password(self, service, username):
            return self._data.get(username)

        def set_password(self, service, username, password):
            self._data[username] = password

        def delete_password(self, service, username):
            self._data.pop(username, None)

    fake = FakeKeyring()
    fake._data[str(vault_dir.resolve())] = key.decode("latin-1")
    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", fake)

    # Add an entry file so list has something to show (encrypted envelope).
    from cipherbox.crypto.aead import encrypt_envelope

    envelope = encrypt_envelope(
        b'{"id":"id-1","schema_version":1,"type":"login","title":"t","tags":[],"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","fields":{}}',
        key,
        b"cipherbox-entry-envelope",
    )
    import json as _json

    (entries_dir / "id-1.json").write_text(
        _json.dumps(envelope, indent=2), encoding="utf-8"
    )

    # list should NOT prompt (keyring hit).
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    out = capsys.readouterr().out
    assert "id-1" in out


def test_unlock_falls_back_to_env_var(tmp_path, monkeypatch, capsys):
    from cipherbox.__main__ import main
    from cipherbox.crypto.kdf import default_kdf_params, derive_key

    vault_dir = tmp_path / "my-vault"
    vault_dir.mkdir()
    entries_dir = vault_dir / "entries"
    entries_dir.mkdir()
    password = "env-pass"
    params = default_kdf_params()
    key = derive_key(password, b"\x03" * 16, params)
    _vault_meta(vault_dir, salt=b"\x03" * 16, params=params)

    # No keyring entry; ensure keyring returns None.
    class EmptyKeyring:
        def get_password(self, service, username):
            return None

        def set_password(self, service, username, password):
            pass

        def delete_password(self, service, username):
            pass

    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", EmptyKeyring())

    # Provide password via env var.
    monkeypatch.setenv("VAULT_PASSWORD", password)

    import json as _json

    from cipherbox.crypto.aead import encrypt_envelope

    envelope = encrypt_envelope(
        b'{"id":"id-1","schema_version":1,"type":"login","title":"t","tags":[],"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","fields":{}}',
        key,
        b"cipherbox-entry-envelope",
    )
    (entries_dir / "id-1.json").write_text(
        _json.dumps(envelope, indent=2), encoding="utf-8"
    )

    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    out = capsys.readouterr().out
    assert "id-1" in out


def test_unlock_wrong_env_password_errors(tmp_path, monkeypatch, capsys):
    import json as _json

    from cipherbox.__main__ import main
    from cipherbox.crypto.aead import encrypt_envelope
    from cipherbox.crypto.kdf import default_kdf_params

    vault_dir = tmp_path / "my-vault"
    vault_dir.mkdir()
    entries_dir = vault_dir / "entries"
    entries_dir.mkdir()
    _vault_meta(vault_dir, salt=b"\x04" * 16, params=default_kdf_params())

    class EmptyKeyring:
        def get_password(self, service, username):
            return None

        def set_password(self, service, username, password):
            pass

        def delete_password(self, service, username):
            pass

    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", EmptyKeyring())
    monkeypatch.setenv("VAULT_PASSWORD", "wrong-password")

    # Planted encrypted entry (won't decrypt with wrong password).
    envelope = encrypt_envelope(
        b'{"id":"id-1","schema_version":1,"type":"login","title":"t","tags":[],'
        b'"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z",'
        b'"fields":{}}',
        b"\x00" * 32,
        b"cipherbox-entry-envelope",
    )
    (entries_dir / "id-1.json").write_text(
        _json.dumps(envelope, indent=2), encoding="utf-8"
    )

    code = main(["list", "--path", str(vault_dir)])
    assert code != 0
    err = capsys.readouterr().err
    assert "error" in err.lower()


def test_unlock_prompt_fallback_when_no_keyring_no_env(tmp_path, monkeypatch, capsys):
    from cipherbox.__main__ import main
    from cipherbox.crypto.kdf import default_kdf_params, derive_key

    vault_dir = tmp_path / "my-vault"
    vault_dir.mkdir()
    entries_dir = vault_dir / "entries"
    entries_dir.mkdir()
    password = "prompt-pass"
    params = default_kdf_params()
    key = derive_key(password, b"\x05" * 16, params)
    _vault_meta(vault_dir, salt=b"\x05" * 16, params=params)

    class EmptyKeyring:
        def get_password(self, service, username):
            return None

        def set_password(self, service, username, password):
            pass

        def delete_password(self, service, username):
            pass

    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", EmptyKeyring())
    monkeypatch.delenv("VAULT_PASSWORD", raising=False)

    import json as _json

    from cipherbox.crypto.aead import encrypt_envelope

    envelope = encrypt_envelope(
        b'{"id":"id-1","schema_version":1,"type":"login","title":"t","tags":[],"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","fields":{}}',
        key,
        b"cipherbox-entry-envelope",
    )
    (entries_dir / "id-1.json").write_text(
        _json.dumps(envelope, indent=2), encoding="utf-8"
    )

    # Provide password via getpass mock.
    inputs = iter([password])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(inputs))

    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    out = capsys.readouterr().out
    assert "id-1" in out
