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
| `bcrypt` | 3.1.7 | Password and credential hashing (`CredentialField`) |
| `rsa` | 4.9.1 | Transitive dependency via `google-auth`; no direct Quay usage |
| `PyNaCl` | 1.5.0 | NaCl bindings (indirect dependency) |
| `pyHanko` | 0.28.0 | Dependency present (no direct in-tree usage found in this audit) |

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

### Docker Schema1 Manifest Signing (v1 registry — dropping)
- **File:** `image/docker/schema1.py`
- **Algorithm:** RS256 via `authlib.jose.JsonWebSignature`
- **Flow:** Signs/verifies Docker v2 schema1 manifests (legacy format)
- **Status:** Will not be ported to Go. Schema1 is superseded by schema2/OCI manifests.

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
- **Operations:** Key generation, JWK thumbprint (RFC 7638) for key ID, PEM serialization, expiry-cached key lookups, cached JWK→public-key conversion
- **Config:** `INSTANCE_SERVICE_KEY_LOCATION`, `INSTANCE_SERVICE_KEY_KID_LOCATION`, `INSTANCE_SERVICE_KEY_EXPIRATION` (default 120 min)

### SSH Key Generation
- **File:** `util/security/ssh.py`
- **Key size:** RSA-2048
- **Purpose:** Docker build trigger SSH keypairs

### CDN URL Signing

| CDN | File | Algorithm | Library |
|-----|------|-----------|---------|
| CloudFront | `storage/cloud.py` | RSA-PKCS1v15 + SHA-1 | `botocore.signers.CloudFrontSigner` |
| CloudFlare | `storage/cloudflarestorage.py` | RSA-PKCS1v15 + SHA-256 | `cryptography` |
| Akamai | `storage/akamaistorage.py` | Edge token signing | `akamai.edgeauth.EdgeAuth` |

### Go migration considerations
- Go stdlib `crypto/rsa` covers all RSA operations
- JWK handling: `github.com/lestrrat-go/jwx/v2/jwk`
- CloudFront: AWS SDK for Go has native CloudFront signer
- CloudFront: Go must use SHA-256 (SHA-1 digital signatures disallowed under FIPS 140-3; AWS supports SHA-256 since 2022)

---

## 4. Symmetric Encryption

### AES-CCM — `v0` (Current — Database Field Encryption)
- **Files:** `data/encryption.py`, `util/security/secret.py`
- **Algorithm:** AES-CCM (Counter with CBC-MAC) — authenticated encryption
- **Nonce:** 13-byte random (`os.urandom`)
- **Key derivation:** Custom cycling/padding of config `DATABASE_SECRET_KEY` to 32 bytes
- **Format:** `v0$$<base64(nonce + ciphertext + tag)>`
- **Usage:** `FieldEncrypter` class encrypts sensitive DB columns via `EncryptedCharField` / `EncryptedTextField`

**Affected database models (8 models, 12 fields):**

| Model | Field(s) | Location |
|-------|----------|----------|
| `RobotAccountToken` | `token` | `data/database.py:861` |
| `AccessToken` | `token_code` | `data/database.py:1153` |
| `RepositoryBuildTrigger` | `secure_auth_token`, `secure_private_key` | `data/database.py:1179-1180` |
| `OAuthApplication` | `secure_client_secret` | `data/database.py:1473` |
| `AppSpecificAuthToken` | `token_secret` | `data/database.py:1692` |
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
- **Algorithm:** SHA-256 (primary), SHA-1 (legacy and utility paths)
- **Library:** `hashlib`
- **Usage:** OCI image content addressing (`sha256:<hex>`), layer checksums

### Additional SHA-1 Usage (Non-primary)
- **Swift temp URL signing:** `storage/swift.py` uses HMAC-SHA1 for temporary download URL signatures (`temp_url_sig`).
- **Kinesis partitioning utility hash:** `data/logs_model/logs_producer/kinesis_stream_logs_producer.py` uses SHA-1 for partition-key derivation (distribution utility, not credential/integrity verification).

### Tarsum (v1 registry — dropping)
- **File:** `digest/checksums.py`
- **Algorithm:** `tarsum+sha256` — SHA-256 of sorted per-file tar header + content hashes
- **Usage:** Docker v1 registry layer verification only (`endpoints/v1/registry.py`)
- **Status:** Deprecated. Docker removed tarsum in 2015 due to non-reproducibility across tar implementations. Only used by the v1 registry protocol which will not be carried forward to Go.

### PKCE Code Challenge
- **File:** `oauth/pkce.py`
- **Algorithm:** SHA-256
- **Usage:** `S256` code challenge method for OAuth 2.0 PKCE

### Go migration considerations
- Go stdlib `crypto/sha256`, `crypto/sha1` — straightforward
- Tarsum, Docker v1 manifest signing (schema1 JWS), and other v1 registry protocol crypto will not be ported to Go

---

## 6. Password Hashing

- **Files:** `data/model/user.py`, `data/fields.py`, `auth/credentials.py`
- **Algorithm:** bcrypt
- **Library:** `bcrypt` (3.1.7)
- **Operations:** `bcrypt.hashpw()` for hashing, `bcrypt.checkpw()`-equivalent via `Credential.matches()`
- **Usage:** User password hashes and other `CredentialField` values (e.g. OAuth auth code/access token credentials).
- **Important distinction:** Robot account tokens and app-specific token secrets are stored with `EncryptedCharField` (AES-CCM), not bcrypt.

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

## 8. CSRF Token Comparison & HMAC

### CSRF token comparison
- **File:** `endpoints/csrf.py`
- **Algorithm/primitive:** Constant-time comparison via `hmac.compare_digest`
- **Usage:** Compares session and request CSRF tokens to mitigate timing side channels
- **Token generation:** 48 bytes from `os.urandom`, base64url-encoded

### HMAC signing
- **File:** `storage/swift.py`
- **Algorithm:** HMAC-SHA1
- **Usage:** Swift temporary URL signature generation (`temp_url_sig`) for direct download URLs

### Go migration considerations
- Go stdlib `crypto/hmac`, `crypto/subtle.ConstantTimeCompare`

---

## 9. FIPS Compliance

- **Config flag:** `FEATURE_FIPS` (default: false)
- **File:** `util/fips.py` — Removes CRAM-MD5 from SMTP auth (MD5 not FIPS compliant)
- **Impact:** When FIPS is enabled, must avoid MD5 and SHA-1 for digital signatures. HMAC-SHA1 remains FIPS-allowed (SP 800-107).

### Go FIPS support (Go 1.24+)
**Note:** The bullets below are external/runtime assumptions for migration planning, not properties validated from this Python repository.

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
| Docker schema1 JWS | N/A | **None** | Legacy v1 protocol — will not be ported to Go |
| Tarsum | N/A | **None** | Legacy v1 protocol — will not be ported to Go |
| FIPS mode | Medium | Medium | Go 1.24 native FIPS module; different algorithm surface than Python/OpenSSL |

---

## 12. AES-CCM → AES-GCM Migration Plan

See [FIPS and Crypto Migration Plan](fips_crypto_migration.md), Section 5 for the full migration plan including phased rollout, Alembic migration design, rollback safety matrix, and interoperability validation requirements.

---

## 13. Additional Recommendations

1. **JWT interoperability is critical.** Registry tokens signed by Python must be verifiable by Go (and vice versa during coexistence). Use the same RSA keys and ensure identical claim validation logic.

2. **bcrypt and SHA-256 are non-issues.** These produce identical, portable outputs in both languages. No migration needed.

3. **Fernet has no Go stdlib equivalent.** Replace with AES-256-GCM during migration, or use `github.com/fernet/fernet-go` as a transitional measure.

4. **Service keys (JWK format)** must remain interoperable. The `authlib` JWK format is standard RFC 7517 — Go's `jwx` library handles this natively.

5. **Go FIPS mode** should be enabled via `GODEBUG=fips140=on` in production. Build with `GOFIPS140=v1.0.0` to pin the certified module version.
