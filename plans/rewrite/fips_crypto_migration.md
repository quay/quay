# FIPS and Crypto Migration Plan

Status: Draft (blocking)
Last updated: 2026-02-26
JIRA: PROJQUAY-10634

## 1. Purpose

Provide a source-anchored migration map for all cryptographic primitives used by Python Quay, define FIPS-compatible Go replacements, and detail the phased AES-CCM → AES-GCM database encryption migration required for Go coexistence.

Supporting documents:
- [Cryptographic Usage Report](crypto_usage_report.md) — full audit of every crypto primitive in the Python codebase

## 2. Source inventory (must preserve behavior)

| Area | Python source anchors | Current primitive(s) | Compatibility risk |
|---|---|---|---|
| DB field encryption | `data/encryption.py` | AES-CCM | **Critical** — not in Go FIPS module |
| Legacy symmetric helper | `util/security/aes.py` | AES-CBC (unauthenticated) | Medium |
| Token/secret helper | `util/security/crypto.py` | Fernet | Medium — no Go stdlib equivalent |
| Registry bearer token signing | `util/security/registry_jwt.py` | JWT RS256 | **High** — core auth path |
| Build token signing | `buildman/build_token.py` | JWT RS256 | High |
| OIDC JWT verification | `oauth/oidc.py` | JWT RS256/RS384 via Authlib | High |
| Security scanner API auth | `util/secscan/v4/api.py` | JWT HS256 | Medium/high |
| External JWT auth | `data/users/externaljwt.py` | JWT verify (PEM public key) | Medium |
| Docker schema1 signing | `image/docker/schema1.py` | JWS RS256 | N/A — will not be ported |
| PKCE challenge generation | `oauth/pkce.py` | SHA-256 | Low |
| Password hashing | `data/fields.py`, `auth/credentials.py` | bcrypt | **None** — portable |
| Content digests | `digest/digest_tools.py` | SHA-256 | **None** — OCI standard |
| Swift temporary URL signing | `storage/swift.py` | HMAC-SHA1 | **None** — HMAC-SHA1 is FIPS-allowed |
| SSH keypair generation | `util/security/ssh.py` | RSA-2048 | Medium |
| CDN signed URLs (CloudFront) | `storage/cloud.py` | RSA PKCS1v15 + SHA-1 | Low — use SHA-256 in Go |
| CDN signed URLs (CloudFlare) | `storage/cloudflarestorage.py` | RSA PKCS1v15 + SHA-256 | Medium |
| CDN signed URLs (Akamai) | `storage/akamaistorage.py` | HMAC token (EdgeAuth) | Medium |
| CSRF token comparison | `endpoints/csrf.py` | `hmac.compare_digest` | Low |
| X.509 / TLS | `util/security/ssl.py` | pyOpenSSL | Low |
| FIPS runtime patching | `util/fips.py` | MD5 restrictions / CRAM-MD5 | **None** — use `smtp.PlainAuth` in Go |
| Tarsum (v1 registry) | `digest/checksums.py` | `tarsum+sha256` | N/A — will not be ported |

### Python crypto dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `cryptography` | 46.0.5 | AES-CBC, AES-CCM, AES-GCM, RSA, Fernet, HKDF |
| `Authlib` | 1.6.5 | JOSE (JWK, JWS, JWE), OAuth/OIDC, JWT |
| `PyJWT` | 2.8.0 | JWT encode/decode |
| `pyOpenSSL` | 25.3.0 | X.509 certificate handling |
| `bcrypt` | 3.1.7 | Password and credential hashing |
| `rsa` | 4.9.1 | CloudFront SHA-1 signing fallback in FIPS environments |

## 3. Implementation decisions

1. All crypto operations route through a Go `internal/cryptoapi` package (no direct ad-hoc crypto in handlers).
2. Go runtime must support two verified profiles: `fips-strict` and `standard`.
3. Python ciphertext compatibility is mandatory before any Go-side write path for encrypted fields.
4. Go FIPS mode enabled via `GODEBUG=fips140=on` in production, built with `GOFIPS140=v1.0.0` to pin the certified module version.

## 4. Algorithm mapping plan

| Contract | Go candidate | FIPS notes | Required action |
|---|---|---|---|
| AES-GCM field encrypt/decrypt (`v1`) | `crypto/aes` + `crypto/cipher.NewGCM` | Approved in Go 1.24 FIPS module | Cross-language test vectors (see PoC) |
| AES-CCM field decrypt (`v0` legacy) | Not needed — migrated before Go deployment | N/A | Startup gate rejects `v0` rows |
| HKDF-SHA256 key derivation (`v1`) | `crypto/hkdf` | FIPS-approved (SP 800-56C) | Identical salt/info constants as Python |
| AES-CBC encrypted basic auth | AES-256-GCM via `cryptoapi` | CBC not needed in Go | Users regenerate encrypted passwords on switchover; no wire-format compat required |
| Fernet envelopes (page tokens) | AES-256-GCM via `cryptoapi` | Ephemeral tokens; no migration needed | Round-trip tests; graceful degradation during rolling deploy |
| RS256 JWS signing | `github.com/golang-jwt/jwt/v5` or `lestrrat-go/jwx` | Must use FIPS-allowed backend keys | Cross-runtime token issue/verify tests |
| Registry JWT RS256 | `github.com/golang-jwt/jwt/v5` | Critical auth path | Must replicate strict claim validation (nbf, iat, exp), `none` rejection |
| OIDC JWT verify | `github.com/golang-jwt/jwt/v5` or `lestrrat-go/jwx` | Must preserve issuer/audience/clock-skew behavior | JWKS fetching + caching parity |
| Secscan JWT HS256 | `github.com/golang-jwt/jwt/v5` | Validate HMAC key handling in FIPS | Clair API auth interop tests |
| PKCE SHA256 | `crypto/sha256` + base64url | FIPS-allowed | RFC 7636 vector tests |
| bcrypt | `golang.org/x/crypto/bcrypt` | Drop-in compatible | No migration needed |
| SHA-256 digests | `crypto/sha256` | OCI standard | No migration needed |
| Swift temp URL HMAC-SHA1 | `crypto/hmac` + `sha1` (or `sha256`) | HMAC-SHA1 is FIPS-allowed; default to SHA-256 for new deployments | Temp URL validation tests with both hash algorithms |
| CloudFront URL signing | `crypto/rsa` PKCS1v15 + **SHA-256** | SHA-1 digital signatures disallowed under FIPS; use SHA-256 | Fixture tests against AWS CloudFront |
| CloudFlare URL signing | `crypto/rsa` PKCS1v15 + SHA-256 | Preferred over SHA-1 | URL signature fixture tests |
| Akamai URL signing | Provider token/HMAC equivalent | Validate algorithm parity with EdgeAuth | Signed token fixture tests |
| RSA key management | `crypto/rsa` + `lestrrat-go/jwx/jwk` | Standard | JWK format interoperability tests |
| X.509 / TLS | `crypto/x509`, `crypto/tls` | Comprehensive stdlib support | SAN matching parity |
| CSRF / HMAC | `crypto/hmac`, `crypto/subtle` | Standard | Trivial |

## 5. AES-CCM → AES-GCM Database Encryption Migration

This is the highest-risk crypto migration item. AES-CCM is not available in Go 1.24's FIPS module, so all encrypted database fields must be migrated to AES-GCM before Go can read them.

### Affected database fields

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

All fields flow through `FieldEncrypter` (`data/encryption.py`) using `DATABASE_SECRET_KEY`.

### Encryption versions

| Parameter | `v0` (current) | `v1` (target) |
|-----------|----------------|---------------|
| Cipher | AES-256-CCM | AES-256-GCM |
| KDF | Byte-cycling (`convert_secret_key`) | HKDF-SHA256 (`derive_key_hkdf`) |
| Nonce | 13 bytes, random | 12 bytes, random |
| Auth tag | CCM tag (appended) | 16-byte GCM tag (appended) |
| Wire format | `v0$$<base64(nonce+ct+tag)>` | `v1$$<base64(nonce+ct+tag)>` |
| FIPS (Python/OpenSSL) | Approved | Approved |
| FIPS (Go 1.24 native) | **Not available** | Approved |

**Why AES-256-GCM:** Present in Go 1.24's FIPS module, AEAD like CCM (no security regression), first-class stdlib support in both languages, dominant industry AEAD mode.

**Why HKDF-SHA256:** Replaces the weak byte-cycling KDF in `util/security/secret.py` (which has a TODO acknowledging this). FIPS-approved (SP 800-56C), available in both Go and Python.

### HKDF parameters (protocol constants)

These values must be identical in Python and Go. They are not configurable.

| Parameter | Value |
|-----------|-------|
| Hash | SHA-256 |
| Salt | `b"quay-field-encryption-v1"` |
| Info | `b"aes-256-gcm"` |
| Output | 32 bytes (AES-256 key) |

### Phased rollout

The migration spans three phases. Each is independently deployable and rollback-safe.

**Why three phases:** This plan must support two deployment models with very different rollback characteristics:
- **Quay.io (continuous deployment):** Deploys frequently; rollbacks between deploys are routine operations. The three-phase approach is primarily designed for this model, where reverting a deploy that switched to `v1` writes must not leave the database in an unreadable state.
- **Red Hat Quay (versioned releases):** y-stream rollbacks (e.g. 3.16 → 3.15) are not supported; z-stream rollbacks are extreme-circumstances-only with support involvement. The phased approach still benefits these customers by protecting against interrupted migrations and providing operational confidence, even though cross-release rollback isn't a supported path.

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

#### Release N — Add `v1` read support

**Goal:** Establish the rollback safety net. No behavior change, no data migration.

**Status:** PoC complete — see branch `PROJQUAY-10634-fips-poc`.

**Python changes:**

1. `data/encryption.py` — Add `v1` entry to `_VERSIONS` dict with `_encrypt_gcm` / `_decrypt_gcm` using AESGCM
2. `util/security/secret.py` — Add `derive_key_hkdf()` using HKDF-SHA256 with fixed salt and info constants. Keep `convert_secret_key()` untouched for `v0` compatibility
3. `data/encryption.py` — `FieldEncrypter.__init__` continues to default to `version="v0"` for writes. The `v1` decrypt path is available but only exercised if a `v1$$` prefixed value is encountered
4. `data/database.py` — `DATABASE_ENCRYPTION_VERSION` config key controls write version (defaults to `"v0"`)

**What this enables:** If a customer upgrades to Release N+1 and rolls back, this release can still read any `v1$$` values written during the N+1 window.

**Testing:**
- Unit test: encrypt with `v1`, decrypt with `v1`
- Unit test: encrypt with `v0`, verify still decryptable
- Unit test: `FieldEncrypter` with `version="v0"` can read `v1$$` values via `decrypt_value()`
- Integration test: round-trip through `EncryptedCharField` with mixed `v0`/`v1` values

#### Release N+1 — Switch writes to `v1`, run migration

**Goal:** All new encrypted values written as `v1`. Existing `v0` values batch-migrated.

**Python changes:**

1. `data/encryption.py` — Change `FieldEncrypter.__init__` default to `version="v1"`
2. Alembic migration — Batch re-encrypt all `v0$$` rows to `v1$$`

**Alembic migration design:**

```python
def upgrade():
    for table, columns in ENCRYPTED_FIELDS.items():
        _migrate_table(table, columns)

def _migrate_table(table, columns):
    conn = op.get_bind()
    encrypter_v0 = FieldEncrypter(secret_key, version="v0")
    encrypter_v1 = FieldEncrypter(secret_key, version="v1")

    for column in columns:
        while True:
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
- **Resumable:** Safe to re-run after interruption
- **No downtime required:** Python reads both versions, so migration runs while serving traffic

**Precedent:** Migration `34c8ef052ec9_repo_mirror_columns.py` already implements a re-encryption pattern for `RepoMirrorConfig` fields.

**Scale considerations:** `RobotAccountToken` and `AccessToken` are the highest-volume tables. At ~5,000–10,000 rows/second (1 decrypt + 1 encrypt + 1 UPDATE per row), a table with 500K rows takes ~1–2 minutes. Release notes should call out that migration time scales with these table sizes.

**Testing:**
- Unit test: migration correctly re-encrypts `v0` → `v1`
- Unit test: migration skips `v1$$` rows
- Unit test: migration is resumable after partial completion
- Scale test: run against representative row counts

#### Release N+2 — Go deployment with startup gate

**Goal:** Go service comes online, reading and writing `v1` only.

**Go implementation:**
1. `v1` encryption/decryption using `crypto/aes` + `crypto/cipher.NewGCM`
2. Key derivation using `crypto/hkdf` with the same salt and info constants
3. Same wire format: `v1$$<base64(nonce+ct+tag)>`

**Startup gate:** Before accepting traffic, Go queries each encrypted table for remaining `v0$$` values:

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

**Python continues unchanged** — reads both `v0` and `v1`, writes `v1` for coexistence.

### Rollback safety matrix

| Scenario | Deployment model | Outcome |
|----------|-----------------|---------|
| Revert deploy after phase N+1 | Quay.io (CD) | Safe — previous deploy reads both `v0` and `v1` |
| Revert deploy after phase N+2 | Quay.io (CD) | Safe — previous deploy reads both `v0` and `v1` |
| Migration interrupted midway | Both | Safe — mix of `v0`/`v1` in DB; Python reads both; re-run to complete |
| Go encounters `v0` row at startup | Both | Blocked — refuses to start with actionable error |
| Go encounters `v0` row at runtime (bug) | Both | `DecryptionFailureException` — `v0` not in Go's version map |

### Upgrade paths

**Quay.io (continuous deployment):** Phases roll out as successive deploys. The primary risk mitigated is rollback between deploys — phase N ensures that reverting a phase N+1 deploy doesn't strand `v1` values in the database.

**Red Hat Quay (versioned releases):**

1. **Upgrade to Release N** — No action required. No behavior change. Quay can now read `v1` values if encountered.
2. **Upgrade to Release N+1** — Alembic migration runs automatically. For large instances, migration may take longer than usual. After migration, all encrypted fields are `v1`.
3. **Upgrade to Release N+2** — Go service becomes available. If migration from N+1 didn't complete, Go startup gate blocks with a clear error.

**Customers who skip releases:** Jumping from pre-N to N+2 gets both `v1` read support and the migration in a single Alembic upgrade. Go startup gate verifies completion.

### Interoperability validation

Before shipping, validate Python ↔ Go ciphertext interoperability:

1. **Python encrypts, Go decrypts** — test vectors
2. **Go encrypts, Python decrypts** — test vectors
3. **HKDF output matches** — same `DATABASE_SECRET_KEY` → same 32-byte key
4. **Wire format matches** — both produce and parse `v1$$<base64(...)>` identically

Cross-language test vectors must be committed to both repositories.

## 6. Legacy key derivation compatibility (`convert_secret_key`)

Current Python behavior (`util/security/secret.py`):
- Derives AES key bytes by repeating raw secret bytes with `itertools.cycle` until exactly 32 bytes
- This is explicitly not a modern KDF, but is compatibility-critical for existing `v0` encrypted values

Go requirement:
- `v0` decryption is **not** needed in Go — the migration in Release N+1 converts all values to `v1` (HKDF-derived key) before Go deployment
- The `convert_secret_key` byte-cycling logic does **not** need to be ported to Go

## 7. Test matrix (blocking)

1. Python `v1` encrypt → Go decrypt fixture tests (cross-language vectors)
2. Go `v1` encrypt → Python decrypt backward tests (during coexistence)
3. HKDF output comparison tests (same key → same derived bytes)
4. FIPS mode startup and smoke test in CI for each target architecture
5. Negative tests for disallowed algorithms when `fips-strict` is enabled
6. Schema1 manifest sign/verify — not ported (v1 protocol dropped)

## 8. Migration risk matrix

| Area | Complexity | Risk | Notes |
|------|-----------|------|-------|
| AES-CCM → AES-GCM DB encryption | High | **Critical** | Phased migration plan defined; PoC complete |
| JWT (RS256/RS384) | Medium | **High** | Core auth; must be bit-compatible |
| Service key management (JWK) | Medium | **High** | Key format must remain interoperable |
| OIDC/JWKS | Medium | Medium | Must replicate key fetching, caching, validation |
| Fernet (page tokens) | Low | Low | Replace with AES-256-GCM; ephemeral tokens, no migration |
| CloudFront signing | Low | Low | Switch to SHA-256; AWS supports it since 2022 |
| AES-CBC (encrypted basic auth) | Low | Low | Client-held tokens; replace with AES-256-GCM, users regenerate |
| X.509/TLS | Low | Low | Go stdlib has excellent support |
| HMAC/CSRF | Low | Low | Trivial in Go |
| bcrypt passwords | Low | **None** | Hash format is cross-platform compatible |
| SHA-256 digests | Low | **None** | OCI standard, identical in Go |
| Docker schema1 JWS | N/A | **None** | Legacy v1 protocol — will not be ported |
| Tarsum | N/A | **None** | Legacy v1 protocol — will not be ported |

## 9. Open questions

1. **`v0` removal timeline:** When can `v0` read support be removed from Python? Requires confidence that no customer deployment has `v0` values remaining. Consider telemetry or a health check endpoint reporting encryption version distribution.
2. **Fernet migration:** ~~`util/security/crypto.py` uses Fernet for transient data. Should this also move to AES-256-GCM, or is `github.com/fernet/fernet-go` acceptable as a transitional measure?~~ **Resolved — replace with AES-256-GCM.** Fernet is used only by `util/pagination.py` to encrypt ephemeral page tokens (`PAGE_TOKEN_KEY`, 2-day TTL) for `endpoints/v2/` and `endpoints/api/`. Tokens are never persisted, decryption failure gracefully returns the first page, and the config comment notes this is for ID-range obfuscation, not security. Reusing the `cryptoapi` AES-256-GCM implementation avoids adding a Go dependency (`fernet-go`) for one non-critical caller. No data migration is needed — during rolling deploys, a token from the old format hitting the new code simply restarts pagination.
3. **AES-CBC:** ~~`util/security/aes.py` uses unauthenticated AES-CBC. Determine if this is still in active use and whether it should be migrated or removed.~~ **Resolved — still active; replace with AES-256-GCM in Go, no data migration.** `AESCipher` has a single consumer: `data/users/__init__.py` (`UserAuthentication.encrypt_user_password` / `_decrypt_user_password`). This implements the "encrypted basic auth" feature (`FEATURE_REQUIRE_ENCRYPTED_BASIC_AUTH`) for external auth backends (LDAP, JWT, Keystone, OIDC). The server encrypts the user's password and returns it via API; the user stores it in `~/.docker/config.json` and presents it in basic auth headers. Encrypted passwords are **never persisted to the database** — they are client-held tokens. Key derivation uses `convert_secret_key(SECRET_KEY)` (byte-cycling KDF, separate from `DATABASE_SECRET_KEY`). When Go takes over these endpoints, implement using AES-256-GCM with HKDF. Users must regenerate their encrypted passwords after the switchover (document in release notes). During Python-only coexistence, no action is needed. The unauthenticated CBC mode is also a security improvement — AES-GCM adds authentication.
4. **SHA-1 signing policy:** ~~Define policy decision for SHA-1 paths (CloudFront/Swift temp URLs) under `fips-strict`.~~ **Resolved — different treatments per FIPS 140-3 / SP 800-131A Rev 2.** SHA-1 for digital signatures is disallowed; SHA-1 for HMAC is allowed. **CloudFront** (`storage/cloud.py:1186`): Uses RSA-PKCS1v15 + SHA-1, which is a digital signature — disallowed under FIPS. AWS has supported SHA-256 for CloudFront signed URLs since 2022 and the Go AWS SDK supports it natively. Go must use SHA-256 for both `fips-strict` and `standard` profiles. **Swift** (`storage/swift.py:231-232`): Uses HMAC-SHA1, which is FIPS-allowed (SP 800-107 places no restriction on SHA-1 for HMAC). No FIPS blocker. Default to HMAC-SHA256 for new deployments (Swift has supported it since Mitaka/2016 via `temp_url_digest`), but HMAC-SHA1 fallback is acceptable even under `fips-strict`. Note: the `rsa` package (4.9.1) listed in the crypto report as a "CloudFront FIPS fallback" is a transitive dependency via `google-auth` with no direct Quay usage — the fallback claim is inaccurate and should be corrected.
5. **CRAM-MD5:** ~~Confirm handling strategy for SMTP edge cases in FIPS mode.~~ **Resolved — trivial; never offer CRAM-MD5 in Go.** Python monkey-patches `smtplib.SMTP.login` via `util/fips.py` to remove CRAM-MD5 (MD5 not FIPS-compliant), leaving only PLAIN and LOGIN. Used in `util/useremails.py` (3 sites) and `notifications/notificationmethod.py` (1 site), all gated on `features.FIPS` with a `MAIL_USE_TLS` assertion. In Go, use `smtp.PlainAuth` exclusively — never `smtp.CRAMMD5Auth`. This requires TLS, which aligns with the existing Python requirement. No feature flag needed; CRAM-MD5 offers no benefit even in `standard` mode.

## 10. Milestone requirements

M0 cannot exit until:
- Crypto inventory is complete and approved.
- Compatibility test corpus exists.
- Explicit fallback behavior is defined for unsupported algorithms.
