# Supported operating systems and filesystems

## Supported operating systems

cipherbox runs on any platform with Python 3.11+:

- **Windows 10/11** (Python 3.11+)
- **macOS** (Python 3.11+)
- **Linux** (Python 3.11+)

No platform-specific dependencies are required. The CLI is a single
entry point, `vault`, installed from PyPI (`pip install cipherbox`) or
from source (`pip install -e .`).

## Default vault location

If `--path` is omitted, the default vault directory is used:

| Platform | Default vault dir |
|----------|-------------------|
| Windows | `%LOCALAPPDATA%/cipherbox-vault` |
| macOS/Linux | `$XDG_DATA_HOME/cipherbox-vault` or `~/.local/share/cipherbox-vault` |

Override with `--path` on any command, e.g. `vault init --path ./my-vault --confirm`.

## Filesystem guidance

- **Local disk only.** Keep the vault on a local filesystem you control.
  cipherbox is designed for a single writer at a time. Network drives,
  FUSE mounts, and object-storage-like filesystems (S3-compatible buckets,
  some synced folders) are not recommended for concurrent or shared access,
  because atomic writes (temp file + fsync + replace) and file-level locking
  are not guaranteed there.
- **One writer at a time.** Two processes writing to the same vault
  simultaneously can produce sync conflicts (duplicate entry IDs across
  files). cipherbox detects these conflicts on `vault list` and never
  silently resolves them; recover manually with `vault backup` /
  `vault restore`.
- **Restrict directory permissions.** Anyone with read access to the vault
  directory can attempt to decrypt entry files; the master password is the
  sole gate. Restrict the vault directory to your user account.
- **Encrypted envelopes.** Once the vault is encrypted, entry files are
  authenticated AES-GCM envelopes (`cipherbox-vault-enc/1`) — never
  plaintext. Plaintext Phase 1 vaults remain readable for backward
  compatibility but are not safe for real credentials.
