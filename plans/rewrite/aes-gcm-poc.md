# AES-GCM (v1) Database Field Encryption — Proof of Concept

**JIRA:** PROJQUAY-10634
**Date:** 2026-02-26
**Status:** PoC
**Related:** [Migration Plan](aes-gcm-migration-plan.md), [Crypto Usage Report](crypto-usage-report.md)

---

## Overview

This PoC implements **Release N** of the [phased migration plan](aes-gcm-migration-plan.md): adding AES-256-GCM (`v1`) read/write support to Python while keeping AES-256-CCM (`v0`) as the default write version. It also includes a reference Go implementation demonstrating cross-language interoperability.

No Alembic migration, no behavior change for existing deployments. Existing `v0$$` encrypted values continue to work unchanged.

---

## What Changed

### Python

| File | Change |
|------|--------|
| `util/security/secret.py` | Extracted `_normalize_secret_key()` from `convert_secret_key()`; added `derive_key_hkdf()` using HKDF-SHA256 |
| `data/encryption.py` | Added `_encrypt_gcm` / `_decrypt_gcm`; extended `EncryptionVersion` with `derive_key` field; added `v1` to `_VERSIONS`; `FieldEncrypter` now stores the raw config key and derives per-version |
| `data/database.py` | `FieldEncrypter` initialization reads `DATABASE_ENCRYPTION_VERSION` from config (defaults to `"v0"`) |
| `data/test/test_encryption.py` | Added v1 test vectors, cross-version decryption test |

### Go (reference implementation)

| File | Purpose |
|------|---------|
| `internal/crypto/encryption.go` | `NormalizeSecretKey`, `DeriveKey` (HKDF-SHA256), `Encrypt`, `Decrypt` — v1 only |
| `internal/crypto/encryption_test.go` | Round-trip tests, cross-language test vectors (decrypts Python-generated ciphertext), HKDF output comparison |

---

## How It Works

### Encryption versions

| Parameter | `v0` (current default) | `v1` (new) |
|-----------|------------------------|------------|
| Cipher | AES-256-CCM | AES-256-GCM |
| KDF | Byte-cycling (`convert_secret_key`) | HKDF-SHA256 (`derive_key_hkdf`) |
| Nonce | 13 bytes | 12 bytes |
| Wire format | `v0$$<base64(nonce+ct+tag)>` | `v1$$<base64(nonce+ct+tag)>` |

### Version-aware decryption

`FieldEncrypter.decrypt_value()` reads the version prefix (`v0$$` or `v1$$`) from the stored value and uses the corresponding decryption function and key derivation. This means:

- A `FieldEncrypter(key, "v0")` can decrypt both `v0$$` and `v1$$` values
- A `FieldEncrypter(key, "v1")` can decrypt both `v0$$` and `v1$$` values
- The `version` parameter only controls which version is used for **writes**

### HKDF parameters (protocol constants)

These values must be identical in Python and Go. They are not configurable.

| Parameter | Value |
|-----------|-------|
| Hash | SHA-256 |
| Salt | `b"quay-field-encryption-v1"` |
| Info | `b"aes-256-gcm"` |
| Output | 32 bytes (AES-256 key) |

---

## Local Dev Evaluation

### Prerequisites

A running local dev environment:

```bash
make local-dev-up
```

### Step 1: Run unit tests

```bash
# Python tests (v0 + v1 encrypt/decrypt, cross-version, test vectors)
TEST=true PYTHONPATH="." pytest data/test/test_encryption.py -v

# Go tests (round-trip, Python cross-language vectors, HKDF comparison)
go test ./internal/crypto/ -v
```

### Step 2: Create a robot account (v0 baseline)

With no config changes, Quay writes `v0$$` values. Create a robot account to generate encrypted data:

1. Open http://localhost:8080 and log in
2. Create an organization (e.g. `testorg`) if one doesn't exist
3. Navigate to the organization → Robot Accounts → Create Robot Account
4. Name it (e.g. `v0robot`)

Verify the token was written as `v0$$`:

```bash
docker exec -it quay-db psql -U quay -d quay -c \
  "SELECT id, substring(token from 1 for 6) AS prefix FROM robotaccounttoken ORDER BY id;"
```

You should see a `v0$$..` prefix.

### Step 3: Switch writes to v1

Add to `conf/stack/config.yaml`:

```yaml
DATABASE_ENCRYPTION_VERSION: v1
```

Restart Quay:

```bash
podman restart quay-quay
```

### Step 4: Create a v1 robot account

Create another robot account through the UI (e.g. `v1robot`), following the same steps as Step 2.

### Step 5: Verify mixed-version reads

Check the database — you should see both `v0$$` (old) and `v1$$` (new) prefixes:

```bash
docker exec -it quay-db psql -U quay -d quay -c \
  "SELECT id, substring(token from 1 for 6) AS prefix FROM robotaccounttoken ORDER BY id;"
```

Both robot accounts should still work. Verify by navigating to each robot account in the UI — Quay should be able to display their token (decrypting both `v0$$` and `v1$$` values).

### Step 6: Verify rollback safety

Switch back to v0 writes by removing `DATABASE_ENCRYPTION_VERSION` from config (or setting it to `v0`) and restarting:

```bash
podman restart quay-quay
```

All `v1$$` values created in Step 4 remain readable — the `v1robot` token should still display in the UI. New robot accounts will be written as `v0$$` again.

### Step 7: Cross-language verification

Verify Go can decrypt Python-produced v1 ciphertext:

```bash
go test ./internal/crypto/ -v -run TestDecryptPythonValues
```

Verify HKDF produces identical keys:

```bash
go test ./internal/crypto/ -v -run TestDeriveKeyMatchesPython
```

---

## What This Does NOT Include

This is Release N only. The following are out of scope:

- **Alembic migration** to re-encrypt existing `v0$$` rows (Release N+1)
- **Default write version change** to `v1` (Release N+1)
- **Go service deployment** or startup gate (Release N+2)
- **`v0` removal** from Python

See [aes-gcm-migration-plan.md](aes-gcm-migration-plan.md) for the full phased rollout.
