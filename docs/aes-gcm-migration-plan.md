# AES-CCM → AES-GCM Database Encryption Migration Plan

**JIRA:** PROJQUAY-10634
**Date:** 2026-02-25
**Status:** Draft

---

## Background

Quay encrypts sensitive database fields (tokens, credentials, secrets) using AES-256-CCM with a versioned wire format (`v0$$<base64(nonce+ct+tag)>`). This is implemented in `data/encryption.py` and applied transparently through `EncryptedCharField` / `EncryptedTextField` in the ORM layer.

As part of the Go migration, the Go service must be able to read and write these encrypted fields. Two constraints make the current `v0` scheme incompatible with Go:

1. **FIPS:** Go 1.24's native FIPS 140-3 module (`crypto/internal/fips140`) does not include AES-CCM. Its supported AES modes are GCM, CBC, CTR, and CMAC. Python's OpenSSL-backed FIPS provider does support CCM, but Go's does not.
2. **Coexistence:** Python and Go will run concurrently against the same database during the transition. Both must agree on the encryption format.

This document describes the plan to migrate from `v0` (AES-CCM) to `v1` (AES-GCM), including the phased rollout across releases, rollback safety, and operational considerations for customer deployments.

---

## Affected Database Fields

8 models, 12 encrypted fields:

| Model | Field(s) | Expected Row Volume |
|-------|----------|-------------------|
| `RobotAccountToken` | `token` | High |
| `AccessToken` | `token_code` | High |
| `AppSpecificAuthToken` | `token_secret` | Medium |
| `RepositoryBuildTrigger` | `secure_auth_token`, `secure_private_key` | Low–Medium |
| `OAuthApplication` | `secure_client_secret` | Low |
| `RepoMirrorConfig` | `external_registry_username`, `external_registry_password` | Low |
| `OrgMirrorConfig` | `external_registry_username`, `external_registry_password` | Low |
| `ProxyCacheConfig` | `upstream_registry_username`, `upstream_registry_password` | Low |

All fields flow through the same `FieldEncrypter` class (`data/encryption.py`) using the `DATABASE_SECRET_KEY` config value, which is processed by `convert_secret_key()` (`util/security/secret.py`) into a 32-byte AES key.

---

## `v1` Encryption Scheme

| Parameter | `v0` (current) | `v1` (target) |
|-----------|----------------|---------------|
| Cipher | AES-256-CCM | AES-256-GCM |
| KDF | Byte-cycling (`convert_secret_key`) | HKDF-SHA256 |
| Nonce | 13 bytes, random | 12 bytes, random |
| Auth tag | CCM tag (appended to ciphertext) | 16-byte GCM tag (appended to ciphertext) |
| Wire format | `v0$$<base64(nonce+ct+tag)>` | `v1$$<base64(nonce+ct+tag)>` |
| FIPS (Python/OpenSSL) | Approved | Approved |
| FIPS (Go 1.24 native) | Not available | Approved |

### Why AES-256-GCM

- Present in Go 1.24's FIPS module (`crypto/internal/fips140/aes/gcm`)
- Present in Python's `cryptography` library under OpenSSL FIPS
- AEAD like CCM — authenticated encryption with no security regression
- First-class stdlib support in both languages (`crypto/cipher.NewGCM` in Go, `cryptography.hazmat.primitives.ciphers.aead.AESGCM` in Python)
- The dominant AEAD mode across the industry

### Why HKDF-SHA256

The current `convert_secret_key()` in `util/security/secret.py` uses a weak byte-cycling scheme to pad the config key to 32 bytes. This is not a proper KDF and has a TODO in the code acknowledging this.

HKDF-SHA256 replaces it:
- FIPS-approved (SP 800-56C)
- Available in Go (`crypto/hkdf`) and Python (`cryptography.hazmat.primitives.kdf.hkdf`)
- Uses a fixed salt and info string to derive the 32-byte AES key deterministically from `DATABASE_SECRET_KEY`

### HKDF Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Hash | SHA-256 | FIPS-approved, available everywhere |
| Salt | Fixed, well-known (e.g. `b"quay-field-encryption-v1"`) | Deterministic derivation from same config key |
| Info | `b"aes-256-gcm"` | Domain separation |
| Output length | 32 bytes | AES-256 key size |

The salt and info values must be identical in both the Python and Go implementations. They should be treated as protocol constants, not configuration.

---

## Phased Rollout

The migration spans three releases. Each release is independently deployable and rollback-safe.

```
                     Python behavior           Go behavior
                     ──────────────────         ─────────────────
Release N:           reads v0 + v1              (not deployed)
                     writes v0

Release N+1:         reads v0 + v1              (not deployed)
                     writes v1
                     migration: v0 → v1

Release N+2:         reads v0 + v1              reads v1 only
                     writes v1                  writes v1
                                                startup gate: rejects v0
```

### Release N — Add `v1` read support

**Goal:** Establish the rollback safety net. No behavior change, no data migration.

**Python changes:**

1. **`data/encryption.py`** — Add `v1` entry to the `_VERSIONS` dict:
   - `_encrypt_gcm(secret_key, value, field_max_length=None)` — HKDF-derive key, generate 12-byte random nonce, encrypt with AESGCM, base64-encode `nonce + ciphertext + tag`
   - `_decrypt_gcm(secret_key, value)` — HKDF-derive key, base64-decode, split nonce from ciphertext, decrypt with AESGCM

2. **`util/security/secret.py`** — Add `derive_v1_key(raw_key)` function using HKDF-SHA256 with the fixed salt and info constants. Keep `convert_secret_key()` untouched for `v0` compatibility.

3. **`data/encryption.py`** — `FieldEncrypter.__init__` continues to default to `version="v0"` for writes. The `v1` decrypt path is available but only exercised if a `v1$$` prefixed value is encountered.

**What this enables:** If a customer later upgrades to Release N+1 and then rolls back, this release can still read any `v1$$` values that were written during the N+1 window.

**Testing:**
- Unit test: encrypt with `v1`, decrypt with `v1`
- Unit test: encrypt with `v0`, verify still decryptable
- Unit test: `FieldEncrypter` with `version="v0"` can read `v1$$` values via `decrypt_value()`
- Integration test: round-trip through `EncryptedCharField` with mixed `v0`/`v1` values

### Release N+1 — Switch writes to `v1`, run migration

**Goal:** All new encrypted values are written as `v1`. Existing `v0` values are batch-migrated.

**Python changes:**

1. **`data/encryption.py`** — Change `FieldEncrypter.__init__` default to `version="v1"`
2. **Alembic migration** — Batch re-encrypt all `v0$$` rows to `v1$$`

**Alembic migration design:**

```python
def upgrade():
    # For each model/field pair
    for table, columns in ENCRYPTED_FIELDS.items():
        _migrate_table(table, columns)

def _migrate_table(table, columns):
    conn = op.get_bind()
    encrypter_v0 = FieldEncrypter(secret_key, version="v0")
    encrypter_v1 = FieldEncrypter(secret_key, version="v1")

    for column in columns:
        while True:
            # Batch of rows still on v0
            rows = conn.execute(
                sa.text(f"SELECT id, {column} FROM {table} "
                        f"WHERE {column} LIKE 'v0$$%' LIMIT 1000")
            ).fetchall()

            if not rows:
                break

            for row in rows:
                plaintext = encrypter_v0.decrypt_value(row[column])
                new_value = encrypter_v1.encrypt_value(plaintext)
                conn.execute(
                    sa.text(f"UPDATE {table} SET {column} = :val WHERE id = :id"),
                    {"val": new_value, "id": row.id}
                )
            conn.commit()
```

**Migration properties:**
- **Batched:** 1000 rows per transaction to avoid long-held locks
- **Idempotent:** `WHERE column LIKE 'v0$$%'` naturally skips already-migrated rows
- **Resumable:** Safe to re-run after interruption — picks up where it left off
- **No downtime required:** Python reads both versions throughout, so the migration can run while the application is serving traffic

**Precedent:** Migration `34c8ef052ec9_repo_mirror_columns.py` already implements a re-encryption pattern for `RepoMirrorConfig` fields. The approach there (decrypt with old encrypter, encrypt with new, batch update) applies directly.

**Testing:**
- Unit test: migration correctly re-encrypts `v0` → `v1`
- Unit test: migration skips `v1$$` rows
- Unit test: migration is resumable after partial completion
- Scale test: run against a database with representative row counts for `RobotAccountToken` and `AccessToken`

### Release N+2 — Go deployment with startup gate

**Goal:** Go service comes online, reading and writing `v1` only.

**Go implementation:**

1. `v1` encryption/decryption using `crypto/aes` + `crypto/cipher.NewGCM`
2. Key derivation using `crypto/hkdf` with the same salt and info constants as Python
3. Same wire format: `v1$$<base64(nonce+ct+tag)>`

**Startup gate:**

Before accepting traffic, Go queries each encrypted table for remaining `v0$$` values:

```sql
SELECT EXISTS(
  SELECT 1 FROM robotaccounttoken WHERE token LIKE 'v0$$%' LIMIT 1
);
-- repeated for each table/column
```

If any `v0` rows are found, Go logs a clear error and exits:

```
FATAL: Found v0-encrypted rows in <table>.<column>.
       Complete the Alembic migration from Release N+1 before starting the Go service.
       Run: alembic upgrade head
```

**Python continues unchanged** — reads both `v0` and `v1`, writes `v1`. This is necessary for coexistence during the transition period.

---

## Rollback Safety Matrix

| Scenario | Outcome |
|----------|---------|
| On N+1, roll back to N | Safe — Release N reads both `v0` and `v1` |
| On N+2, roll back to N+1 | Safe — Release N+1 reads both `v0` and `v1` |
| Migration interrupted midway | Safe — DB has mix of `v0`/`v1`; Python reads both; re-run migration to complete |
| Go encounters `v0` row at startup | Blocked — refuses to start with actionable error message |
| Go encounters `v0` row at runtime (bug) | `DecryptionFailureException` — `v0` is not in Go's version map |

---

## Customer Upgrade Path

From a customer's perspective, this is a standard multi-release upgrade:

1. **Upgrade to Release N** — No action required. No behavior change. Quay can now read `v1` values if it encounters them.
2. **Upgrade to Release N+1** — Alembic migration runs automatically during deployment. For large instances, the migration may take longer than usual (see scale considerations below). After migration, all encrypted fields are `v1`.
3. **Upgrade to Release N+2** (or later) — Go service becomes available. If the Alembic migration from N+1 didn't complete (e.g., customer skipped N+1), the Go startup gate will block with a clear error.

**Customers who skip releases:** A customer jumping from pre-N directly to N+2 will get both the `v1` read support (from N) and the migration (from N+1) in a single Alembic upgrade. The Go startup gate will verify completion before starting.

---

## Scale Considerations

The two highest-volume tables are `RobotAccountToken` and `AccessToken`. For large enterprise deployments, these could contain hundreds of thousands of rows.

**Estimated migration throughput:** Each row requires one AES-CCM decrypt + one AES-GCM encrypt + one UPDATE. At 1000 rows/batch with typical DB latency, expect roughly 5,000–10,000 rows/second. A table with 500K rows would take ~1–2 minutes.

**Mitigations for large deployments:**
- Batched transactions prevent lock contention
- Migration can run online (Quay continues serving traffic)
- Migration is resumable if the deployment process has a timeout
- Release notes should call out that the migration time scales with `RobotAccountToken` and `AccessToken` row counts

---

## Interoperability Validation

Before shipping, validate that Python and Go produce interoperable ciphertext:

1. **Python encrypts, Go decrypts** — Generate test vectors in Python, verify Go can decrypt
2. **Go encrypts, Python decrypts** — Generate test vectors in Go, verify Python can decrypt
3. **HKDF output matches** — Given the same `DATABASE_SECRET_KEY`, both implementations must derive the same 32-byte AES key
4. **Wire format matches** — Both implementations must produce and parse `v1$$<base64(...)>` identically

These should be captured as cross-language test vectors committed to both repositories.

---

## Open Questions

1. **Salt/info constants:** Final values for the HKDF salt and info string need to be decided and documented as protocol constants.
2. **`v0` removal timeline:** When can `v0` read support be removed from Python? This requires confidence that no customer deployment has `v0` values remaining. Consider adding telemetry or a health check endpoint that reports encryption version distribution.
3. **Fernet migration:** `util/security/crypto.py` uses Fernet for transient data encryption. Should this also move to AES-256-GCM, or is a Go Fernet library (`github.com/fernet/fernet-go`) acceptable?
4. **AES-CBC:** `util/security/aes.py` uses unauthenticated AES-CBC. Determine if this is still in active use and whether it should be migrated or removed.
