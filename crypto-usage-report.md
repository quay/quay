# Cryptographic Usage Report — Quay Python Codebase

**Date:** 2026-02-24
**Purpose:** Audit of cryptographic usage to inform Go migration planning (PROJQUAY-10634)

---

## 1. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `cryptography` | 46.0.5 | AES-CBC, AES-CCM, RSA key generation, Fernet, serialization |
| `Authlib` | 1.6.5 | JOSE (JWK, JWS, JWE), OAuth/OIDC, JWT signing/verification |
| `PyJWT` | 2.8.0 | JWT encode/decode |
| `pyOpenSSL` | 25.3.0 | X.509 certificate loading, validation, SAN extraction |
| `bcrypt` | 3.1.7 | Password hashing (users, robot tokens) |
| `PyNaCl` | 1.5.0 | NaCl bindings (indirect dependency) |
| `pyHanko` | 0.28.0 | PDF signing |

**System packages (Dockerfile):** `openssl`, `openssl-devel`, `libffi-devel`

---

## 2. JWT / JWS Operations

**This is the single largest area of crypto usage.**

### Registry Bearer Tokens
- **Files:** `util/security/registry_jwt.py`, `util/security/jwtutil.py`
- **Algorithm:** RS256 (RSA PKCS1v15 + SHA-256)
- **Library:** PyJWT + Authlib
- **Flow:** Quay signs bearer tokens with instance RSA private key; clients present them for registry v2 API auth
- **Config:** `REGISTRY_JWT_AUTH_MAX_FRESH_S` (default 3660s), 30s clock skew tolerance
- **Strict validation:** Rejects `alg: none`, requires `nbf`, `iat`, `exp` claims

### Build Tokens
- **File:** `buildman/build_token.py`
- **Algorithm:** RS256
- **Flow:** Buildman generates/verifies JWT tokens for build job authentication

### OIDC Token Verification
- **File:** `oauth/oidc.py`
- **Algorithms:** RS256, RS384
- **Library:** Authlib (JsonWebKey, KeySet)
- **Flow:** Fetches JWKS from OIDC provider, verifies ID tokens, caches public keys (1h TTL)

### External JWT Auth
- **File:** `data/users/externaljwt.py`
- **Flow:** Loads PEM public key certificate, verifies externally-signed JWTs for federated auth

### Docker Schema1 Manifest Signing
- **File:** `image/docker/schema1.py`
- **Algorithm:** RS256 via `authlib.jose.JsonWebSignature`
- **Flow:** Signs/verifies Docker v2 schema1 manifests (legacy format)

### Go migration considerations
- Go equivalents: `github.com/golang-jwt/jwt/v5`, `github.com/lestrrat-go/jwx/v2`
- Must support RS256, RS384, HS256 algorithms
- Must replicate strict claim validation (nbf, iat, exp) and `none` algorithm rejection
- JWKS fetching + caching for OIDC
- JWS (JSON Web Signature) for schema1 manifests

---

## 3. RSA Key Management

### Instance Service Keys
- **Files:** `data/model/service_keys.py`, `util/security/instancekeys.py`
- **Key size:** RSA-2048
- **Library:** `cryptography.hazmat.primitives.asymmetric.rsa`, Authlib `JsonWebKey`
- **Operations:** Key generation, JWK thumbprint (RFC 7638) for key ID, PEM serialization, LRU-cached public key lookups
- **Config:** `INSTANCE_SERVICE_KEY_LOCATION`, `INSTANCE_SERVICE_KEY_KID_LOCATION`, `INSTANCE_SERVICE_KEY_EXPIRATION` (default 120 min)

### SSH Key Generation
- **File:** `util/security/ssh.py`
- **Key size:** RSA-2048
- **Purpose:** Docker build trigger SSH keypairs

### CDN URL Signing

| CDN | File | Algorithm | Library |
|-----|------|-----------|---------|
| CloudFront | `storage/cloud.py` | RSA-PKCS1v15 + SHA-1 | `botocore.signers.CloudFrontSigner` |
| CloudFront (FIPS fallback) | `storage/cloud.py` | Pure-Python RSA (when SHA-1 blocked by system crypto policy) | `rsa` |
| CloudFlare | `storage/cloudflarestorage.py` | RSA-PKCS1v15 + SHA-256 | `cryptography` |
| Akamai | `storage/akamaistorage.py` | Edge token signing | `akamai.edgeauth.EdgeAuth` |

### Go migration considerations
- Go stdlib `crypto/rsa` covers all RSA operations
- JWK handling: `github.com/lestrrat-go/jwx/v2/jwk`
- CloudFront: AWS SDK for Go has native CloudFront signer
- SHA-1 signing may conflict with FIPS mode in Go as well — need equivalent fallback strategy

---

## 4. Symmetric Encryption

### AES-CCM — `v0` (Current — Database Field Encryption)
- **Files:** `data/encryption.py`, `util/security/secret.py`
- **Algorithm:** AES-CCM (Counter with CBC-MAC) — authenticated encryption
- **Nonce:** 13-byte random (`os.urandom`)
- **Key derivation:** Custom cycling/padding of config `DATABASE_SECRET_KEY` to 32 bytes
- **Format:** `v0$$<base64(nonce + ciphertext + tag)>`
- **Usage:** `FieldEncrypter` class encrypts sensitive DB columns via `EncryptedCharField` / `EncryptedTextField`

**Affected database models (7 models, 10 fields):**

| Model | Field(s) | Location |
|-------|----------|----------|
| `RobotAccountToken` | `token` | `data/database.py:861` |
| `AccessToken` | `token_code` | `data/database.py:1153` |
| `RepositoryBuildTrigger` | `secure_auth_token`, `secure_private_key` | `data/database.py:1179-1180` |
| `OAuthApplication` | `secure_client_secret` | `data/database.py:1473` |
| `AppSpecificToken` | `token_secret` | `data/database.py:1692` |
| `RepoMirrorConfig` | `external_registry_username`, `external_registry_password` | `data/database.py:1902-1903` |
| `OrgMirrorConfig` | `external_registry_username`, `external_registry_password` | `data/database.py:1992-1993` |
| `ProxyCacheConfig` | `upstream_registry_username`, `upstream_registry_password` | `data/database.py:2111-2112` |

**Key derivation weakness:** `util/security/secret.py:7` has a TODO noting the KDF is weak — it cycles raw key bytes to 32 bytes rather than using a proper KDF (HKDF, PBKDF2, etc.).

**Encryption key flow:**
```
config["DATABASE_SECRET_KEY"]
  → convert_secret_key()          [util/security/secret.py]
  → FieldEncrypter(secret_key)    [data/encryption.py:66]
  → db_encrypter.initialize(...)  [data/database.py:592]
  → BaseModel._meta.encrypter     [data/database.py:740]
  → EncryptedCharField / EncryptedTextField read/write
```

### AES-CBC (Secondary)
- **File:** `util/security/aes.py`
- **Algorithm:** AES-CBC with PKCS7 padding
- **IV:** Random 16 bytes
- **Not authenticated** — no HMAC or GCM

### Fernet (Transient Data)
- **File:** `util/security/crypto.py`
- **Library:** `cryptography.fernet.Fernet`
- **Usage:** Symmetric authenticated encryption with TTL-based expiration
- **Key:** 32-byte key required

---

## 5. Hashing

### Content-Addressable Digests
- **Files:** `digest/digest_tools.py`, `digest/checksums.py`
- **Algorithm:** SHA-256 (primary), SHA-1 (legacy schema1)
- **Library:** `hashlib`
- **Usage:** OCI image content addressing (`sha256:<hex>`), layer checksums, tarsum

### PKCE Code Challenge
- **File:** `oauth/pkce.py`
- **Algorithm:** SHA-256
- **Usage:** `S256` code challenge method for OAuth 2.0 PKCE

### Go migration considerations
- Go stdlib `crypto/sha256`, `crypto/sha1` — straightforward
- Tarsum implementation needs porting (`digest/checksums.py`)

---

## 6. Password Hashing

- **Files:** `data/model/user.py`, `data/fields.py`, `auth/credentials.py`
- **Algorithm:** bcrypt
- **Library:** `bcrypt` (3.1.7)
- **Operations:** `bcrypt.hashpw()` for hashing, `bcrypt.checkpw()` equivalent via `Credential.matches()`
- **Usage:** User passwords, robot account tokens, app-specific tokens

### Go migration considerations
- Go: `golang.org/x/crypto/bcrypt` — drop-in compatible, same hash format
- Existing bcrypt hashes are portable between Python and Go with no migration needed

---

## 7. TLS / Certificate Handling

### Certificate Validation
- **File:** `util/security/ssl.py`
- **Library:** pyOpenSSL (`OpenSSL.crypto`)
- **Operations:**
  - Load PEM X.509 certificates
  - Validate private key matches certificate
  - Extract Subject Alternative Names (SAN) for DNS matching
  - Check certificate expiration

### Configuration Keys
| Key | Purpose |
|-----|---------|
| `EXTERNAL_TLS_TERMINATION` | Whether TLS terminates before Quay |
| `SSL_CIPHERS` | Nginx cipher suite list |
| `SSL_PROTOCOLS` | Allowed TLS protocol versions |
| `PREFERRED_URL_SCHEME` | `https` when TLS enabled |
| `SESSION_COOKIE_SECURE` | Secure cookie flag |
| `REPO_MIRROR_TLS_VERIFY` | Verify certs during mirror (default: true) |

### Go migration considerations
- Go stdlib `crypto/x509`, `crypto/tls` — comprehensive built-in support
- `x509.ParseCertificate`, `x509.Certificate.VerifyHostname` for SAN matching

---

## 8. HMAC & CSRF

- **File:** `endpoints/csrf.py`
- **Algorithm:** HMAC (implicit via `hmac.compare_digest`)
- **Usage:** Constant-time CSRF token comparison to prevent timing attacks
- **Token generation:** 48 bytes from `os.urandom`, base64url-encoded

### Go migration considerations
- Go stdlib `crypto/hmac`, `crypto/subtle.ConstantTimeCompare`

---

## 9. FIPS Compliance

- **Config flag:** `FEATURE_FIPS` (default: false)
- **File:** `util/fips.py` — Removes CRAM-MD5 from SMTP auth (MD5 not FIPS compliant)
- **CloudFront fallback:** `storage/cloud.py` — Falls back to pure-Python RSA when system crypto policy blocks SHA-1
- **Impact:** When FIPS is enabled, must avoid MD5, SHA-1 in security contexts

### Go FIPS support (Go 1.24+)
- Go 1.24 includes a **native FIPS 140-3 cryptographic module** (`crypto/internal/fips140`)
- Enabled at runtime via `GODEBUG=fips140=on` (or `fips140=only` for strict mode)
- No cgo or BoringCrypto dependency required — pure Go implementation
- Module v1.0.0 has CAVP certificate A6650 (in review)
- Available AES modes in the FIPS module: **GCM, CBC, CTR, CMAC** — notably **AES-CCM is not included**
- Also includes: HKDF, PBKDF2, ECDSA, RSA, SHA-2, HMAC

---

## 10. Random Number Generation

| Location | Method | Purpose |
|----------|--------|---------|
| `data/encryption.py` | `os.urandom(13)` | AES-CCM nonce |
| `util/security/aes.py` | `os.urandom(16)` | AES-CBC IV |
| `endpoints/csrf.py` | `os.urandom(48)` | CSRF tokens |
| `oauth/pkce.py` | `secrets.choice()` | PKCE code verifier |
| `data/fields.py` | `SystemRandom` | Credential generation |

### Go migration considerations
- Go stdlib `crypto/rand.Read` — single unified CSPRNG

---

## 11. Summary: Migration Risk Matrix

| Area | Complexity | Risk | Notes |
|------|-----------|------|-------|
| JWT (RS256/RS384) | Medium | **High** | Core auth mechanism; must be bit-compatible |
| Service key management | Medium | **High** | Key format (JWK/PEM) must remain interoperable |
| AES-CCM DB encryption | High | **Critical** | Not in Go's FIPS module; requires migration to AES-GCM (see Section 12) |
| AES-CBC | Low | Low | Standard algorithm |
| bcrypt passwords | Low | **None** | Hash format is cross-platform compatible |
| SHA-256 digests | Low | **None** | OCI standard, identical in Go |
| X.509/TLS | Low | Low | Go stdlib has excellent support |
| CloudFront signing | Medium | Medium | SHA-1 + FIPS fallback path |
| OIDC/JWKS | Medium | Medium | Must replicate key fetching, caching, validation |
| HMAC/CSRF | Low | Low | Trivial in Go |
| Fernet | Medium | Medium | No Go stdlib equivalent; consider replacing with AES-GCM |
| Docker schema1 JWS | Medium | Low | Legacy format, may not need long-term support |
| FIPS mode | Medium | Medium | Go 1.24 native FIPS module; different algorithm surface than Python/OpenSSL |

---

## 12. AES-CCM → AES-GCM Migration Plan

### Problem

The current `v0` database field encryption uses AES-CCM. Go 1.24's native FIPS 140-3 module does not include AES-CCM — it supports AES-GCM, AES-CBC, AES-CTR, and CMAC. Python and Go must coexist reading/writing the same database during migration, and customer-paced upgrades mean we cannot force a hard cutover.

### Target: `v1` Encryption Scheme

| Parameter | `v0` (current) | `v1` (target) |
|-----------|----------------|---------------|
| Cipher | AES-256-CCM | **AES-256-GCM** |
| KDF | Byte-cycling (weak) | **HKDF-SHA256** |
| Nonce | 13 bytes | **12 bytes** (GCM standard) |
| Auth tag | CCM tag | **16-byte GCM tag** |
| Wire format | `v0$$<base64(nonce+ct+tag)>` | `v1$$<base64(nonce+ct+tag)>` |
| FIPS status (Python/OpenSSL) | Approved | Approved |
| FIPS status (Go 1.24 native) | **Not available** | Approved |

**Why AES-256-GCM:**
- FIPS-approved and present in Go 1.24's native FIPS module (`crypto/internal/fips140/aes/gcm`)
- FIPS-approved in Python's `cryptography` library (OpenSSL FIPS provider)
- AEAD like AES-CCM — provides both confidentiality and authenticity, no security regression
- First-class Go stdlib support via `crypto/aes` + `crypto/cipher.NewGCM`

**Why HKDF-SHA256:**
- Replaces the weak byte-cycling KDF in `util/security/secret.py`
- FIPS-approved (SP 800-56C)
- Available in Go (`crypto/hkdf`) and Python (`cryptography.hazmat.primitives.kdf.hkdf`)

### Phased Rollout

The migration is structured across three releases to ensure safe rollback at every stage. Python and Go coexist — Go only starts once re-encryption is complete.

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

#### Release N — Add `v1` read support (rollback safety net)

**Changes:**
- Add `v1` entry to `_VERSIONS` dict in `data/encryption.py` with AES-GCM + HKDF implementation
- Python can read both `v0` and `v1` but continues writing `v0`
- No data migration, no behavior change

**Why:** If a customer upgrades to Release N+1 (which writes `v1`) and needs to roll back, the previous release can still read the `v1` values it encounters. Without this, rollback from N+1 would produce `DecryptionFailureException` on any rows that were written as `v1`.

#### Release N+1 — Migrate `v0 → v1`

**Changes:**
- Python writes `v1` for all new/updated encrypted values
- Ship an Alembic migration that batch-re-encrypts all `v0$$` rows to `v1$$`
- Migration must be:
  - **Batched** — process ~1000 rows per transaction to avoid long locks
  - **Idempotent** — skip rows already prefixed with `v1$$`
  - **Resumable** — safe to re-run if interrupted

**Affected tables and estimated scale concern:**

| Model | Likely row count | Notes |
|-------|-----------------|-------|
| `RobotAccountToken` | High | One per robot account |
| `AccessToken` | High | Accumulates over time |
| `AppSpecificToken` | Medium | User-created |
| `OAuthApplication` | Low | One per OAuth app |
| `RepositoryBuildTrigger` | Low-Medium | One per build trigger |
| `RepoMirrorConfig` | Low | One per mirrored repo |
| `OrgMirrorConfig` | Low | One per org mirror |
| `ProxyCacheConfig` | Low | One per proxy cache |

**Precedent:** Migration `34c8ef052ec9_repo_mirror_columns.py` already re-encrypts fields with key rotation support. The pattern there (decrypt with old, encrypt with new, batch update) applies directly.

#### Release N+2 — Go deployment with startup gate

**Changes:**
- Go implements `v1` only (AES-256-GCM + HKDF-SHA256)
- On startup, Go queries each encrypted table for remaining `v0$$` prefixes
- If any `v0` rows exist, Go refuses to start with a clear error directing the operator to complete the Alembic migration
- Python continues to support both `v0` read and `v1` read/write for coexistence

**Startup gate query (per table):**
```sql
SELECT EXISTS(
  SELECT 1 FROM <table> WHERE <encrypted_column> LIKE 'v0$$%' LIMIT 1
);
```

### Rollback Safety

| Scenario | Outcome |
|----------|---------|
| Customer on N+1, rolls back to N | Safe — N reads both `v0` and `v1` |
| Customer on N+2, rolls back to N+1 | Safe — N+1 reads both `v0` and `v1` |
| Migration interrupted midway | Safe — mix of `v0` and `v1` in DB; Python reads both; re-run migration to finish |
| Go encounters `v0` row | Blocked at startup — does not silently fail |

---

## 13. Additional Recommendations

1. **JWT interoperability is critical.** Registry tokens signed by Python must be verifiable by Go (and vice versa during coexistence). Use the same RSA keys and ensure identical claim validation logic.

2. **bcrypt and SHA-256 are non-issues.** These produce identical, portable outputs in both languages. No migration needed.

3. **Fernet has no Go stdlib equivalent.** Replace with AES-256-GCM during migration, or use `github.com/fernet/fernet-go` as a transitional measure.

4. **Service keys (JWK format)** must remain interoperable. The `authlib` JWK format is standard RFC 7517 — Go's `jwx` library handles this natively.

5. **Go FIPS mode** should be enabled via `GODEBUG=fips140=on` in production. Build with `GOFIPS140=v1.0.0` to pin the certified module version.
