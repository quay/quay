# FIPS and Crypto Migration Plan

Status: Draft (blocking)
Last updated: 2026-02-09

## 1. Purpose

Provide a source-anchored migration map for all cryptographic primitives used by Python Quay and define FIPS-compatible Go replacements.

## 2. Source inventory (must preserve behavior)

| Area | Python source anchors | Current primitive(s) | Compatibility risk |
|---|---|---|---|
| DB field encryption | `data/encryption.py` | AES-CCM | High (existing ciphertext readability) |
| Legacy symmetric helper | `util/security/aes.py` | AES-CBC | Medium |
| Token/secret helper | `util/security/crypto.py` | Fernet-style envelope | High |
| Registry schema1 signing | `image/docker/schema1.py` | JWS RS256 | High |
| Registry bearer token signing | `util/security/registry_jwt.py` | JWT RS256 | High |
| OIDC JWT verification | `oauth/oidc.py` | JWT verify (`RS256`/allowed list) | High |
| Security scanner API auth | `util/secscan/v4/api.py` | JWT HS256 | Medium/high |
| PKCE challenge generation | `oauth/pkce.py` | SHA-256 | Low/medium |
| Swift temporary URL signing | `storage/swift.py` | HMAC-SHA1 | High in FIPS-strict |
| SSH keypair generation | `util/security/ssh.py` | RSA-2048 key generation | Medium |
| CDN signed URLs (CloudFront) | `storage/cloud.py` | RSA PKCS1v15 + SHA1 | High in FIPS-strict |
| CDN signed URLs (CloudFlare) | `storage/cloudflarestorage.py` | RSA PKCS1v15 + SHA256 | Medium |
| CDN signed URLs (Akamai) | `storage/akamaistorage.py` | HMAC token (EdgeAuth) | Medium |
| FIPS runtime patching | `util/fips.py` | MD5 restrictions/CRAM-MD5 handling | High |
| Avatar hashing path | `avatars/avatars.py` | MD5 (blocked in FIPS mode) | Low/medium |

## 3. Implementation decisions

1. All crypto operations route through a Go `internal/cryptoapi` package (no direct ad-hoc crypto in handlers).
2. Go runtime must support two verified profiles:
- `fips-strict`
- `standard`
3. Python ciphertext compatibility is mandatory before any Go-side write path for encrypted fields.

## 4. Algorithm mapping plan

| Contract | Go candidate | FIPS notes | Required action |
|---|---|---|---|
| AES-CCM field decrypt/encrypt | `crypto/cipher` + vetted CCM implementation | Confirm availability/validation under selected FIPS build | Build fixture test corpus and run in FIPS CI |
| AES-CBC legacy helper | `crypto/aes` + CBC mode wrapper | Allowed with approved key/IV handling policy | Preserve wire format where still active |
| Fernet-like envelopes | compatibility wrapper over AES/HMAC primitives | Validate timestamp/token format parity | Golden-token parse/verify tests |
| RS256 JWS signing | JOSE library with RS256 support | Must use FIPS-allowed backend keys | Schema1 manifest signing/parsing parity tests |
| Registry JWT RS256 | `github.com/golang-jwt/jwt/v5` + FIPS-approved crypto backend | Critical auth path for registry operations | Cross-runtime token issue/verify tests with existing keys |
| OIDC JWT verify | `github.com/golang-jwt/jwt/v5` or `lestrrat-go/jwx` | Must preserve issuer/audience/clock-skew behavior | OIDC token validation fixture corpus |
| Secscan JWT HS256 | `github.com/golang-jwt/jwt/v5` | Validate HMAC key handling in FIPS profiles | Clair API auth interoperability tests |
| PKCE SHA256 | `crypto/sha256` + base64url | Generally FIPS-allowed | RFC7636 vector tests |
| Swift temp URL HMAC-SHA1 | `crypto/hmac` + `sha1` | SHA1 policy must be explicitly allowed or phased migration defined | Temp URL validation tests against Swift |
| CloudFront URL signing | `crypto/rsa` PKCS1v15 + SHA1 | SHA1 signing risk in strict profiles | Fixture tests + policy/exception signoff |
| CloudFlare URL signing | `crypto/rsa` PKCS1v15 + SHA256 | Preferred over SHA1 for strict profiles | URL signature fixture tests |
| Akamai URL signing | provider token/HMAC equivalent | Validate algorithm parity with EdgeAuth behavior | Signed token fixture tests |

## 5. AES key derivation compatibility (`convert_secret_key`)

Current Python behavior:
- `util/security/secret.py` derives AES key bytes by repeating raw secret bytes with `itertools.cycle` until exactly 32 bytes.
- This is explicitly not a modern KDF, but is compatibility-critical for existing encrypted values.

Go requirement:
- Reproduce byte-for-byte equivalent derivation for legacy compatibility.
- Do not substitute Argon2/PBKDF2/salt-based KDF for existing key material without a formal migration plan.

Mandatory compatibility tests:
1. Fixed input secret -> expected 32-byte derived output vector (Python oracle).
2. Python-encrypted value decrypts in Go.
3. Go-encrypted value decrypts in Python (during mixed runtime).
4. FIPS profile run confirms selected implementation is accepted in target environment.

## 6. Test matrix (blocking)

1. Python-encrypted -> Go-decrypted fixture tests.
2. Go-encrypted -> Python-decrypted backward tests (until Python retirement).
3. Schema1 manifest sign/verify cross-runtime tests.
4. FIPS mode startup and smoke test in CI for each target architecture.
5. Negative tests for disallowed algorithms when `fips-strict` is enabled.

## 7. Open technical checks

- Confirm final Go toolchain/build profile for FIPS (`GOFIPS140` + toolchain constraints).
- Confirm AES-CCM implementation acceptance in target compliance environment.
- Confirm CRAM-MD5 handling strategy for SMTP edge cases in FIPS mode.
- Define policy decision for SHA1-signing paths (CloudFront/Swift temp URLs) under `fips-strict`.

## 8. Milestone requirements

M0 cannot exit until:
- crypto inventory is complete and approved.
- compatibility test corpus exists.
- explicit fallback behavior is defined for unsupported algorithms.
