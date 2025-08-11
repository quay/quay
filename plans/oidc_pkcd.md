### OIDC PKCE Support: Scope, Gaps, and Implementation Plan

#### Current State (from code review)
- OIDC exists via `oauth/oidc.py` with discovery, Authorization Code flow, `id_token` verification (JWKS), and optional `userinfo` fetch.
- Authorization URL is built by `OAuthService.get_auth_url()` with params: `client_id`, `redirect_uri`, `scope`, `state`.
- Token exchange is handled by `OAuthService.exchange_code()`; payload includes: `code`, `grant_type=authorization_code`, `redirect_uri`, `client_id`, `client_secret`.
- No PKCE support found: no `code_challenge`, `code_challenge_method`, or `code_verifier` usage.
- Session `state` is CSRF-oriented and stable per session; not unique per auth request.
- Additional OIDC usages: SSO JWT validation for API v1 (`auth/oauth.validate_sso_oauth_token`), federated robot tokens (`util/security/federated_robot_auth.py`).

#### Goal
Add optional PKCE (RFC 7636) support to OIDC login flows. When enabled per OIDC provider:
- Include `code_challenge` and `code_challenge_method` on the authorization request.
- Include matching `code_verifier` in the token exchange.
- Support `S256` (preferred) and fallback `plain`.
- Allow “public client” mode (omit client secret on token exchange) behind config.

### Phased Implementation Plan

#### Phase 1: Config and Capability Wiring
- Add OIDC service-level config keys (per service block like `SOMEOIDC_LOGIN_CONFIG`):
  - `USE_PKCE: true|false` (default false)
  - `PKCE_METHOD: "S256"|"plain"` (default "S256")
  - `PUBLIC_CLIENT: true|false` (default false). When true, do not send `client_secret` and use HTTP Basic auth only if provider requires, otherwise none.
- Extend config schema (`util/config/schema.py`) with the above keys under a generic OIDC provider object (documented but schema may currently not enumerate arbitrary OIDC providers; minimally document in `docs/`).

Deliverables:
- Schema/docs updates; no runtime behavior change yet.

#### Phase 2: PKCE Auth URL and Token Exchange
Minimal, backward-compatible API changes in the OAuth layer:
- In `oauth/base.py`:
  - Extend `OAuthService.get_auth_url(..., extra_auth_params: dict = None)` to merge extra query params.
  - Extend `OAuthService.exchange_code(..., extra_token_params: dict = None, ...)` to merge extra body params.
  - Keep existing callers working (new params default to None).
- Create `oauth/pkce.py` helpers:
  - `generate_code_verifier(length=64)` → random RFC 7636-compliant string (43–128 chars).
  - `code_challenge(verifier, method="S256")` → base64url(SHA256(verifier)) or `verifier` for plain.
- In `oauth/oidc.py` (`OIDCLoginService`):
  - Add:
    - `def pkce_enabled(self): return bool(self.config.get("USE_PKCE", False))`
    - `def pkce_method(self): return self.config.get("PKCE_METHOD", "S256")`
  - Update `exchange_code_for_tokens(..., code_verifier=None, ...)` to pass `extra_token_params={"code_verifier": code_verifier}` when PKCE is enabled.
  - Respect `PUBLIC_CLIENT`: when true, call `exchange_code(..., client_auth=False)` and omit `client_secret` (current code already uses payload-based client auth; ensure secret is omitted if `PUBLIC_CLIENT` is true).

Endpoint-layer session handling (Flask) so services stay framework-agnostic:
- In `endpoints/api/user.py` (`ExternalLoginInformation.post`):
  - If `pkce_enabled`, generate a `code_verifier`, compute `code_challenge`, store verifier in session under a namespaced key, e.g. `session[f"_oauth_pkce_{service_id}"] = {"verifier": v, "ts": now}`.
  - Call `login_service.get_auth_url(..., extra_auth_params={"code_challenge": cc, "code_challenge_method": method})`.
- In `endpoints/oauth/login.py` callbacks (`callback_func`, `attach_func`, `cli_token_func`):
  - Retrieve and pop `session[f"_oauth_pkce_{service_id}"]` if present and `pkce_enabled`.
  - Pass the verifier into `login_service.exchange_code_for_login(..., code_verifier=verifier)` (plumb param through `exchange_code_for_tokens`).

Security/robustness:
- Set short TTL (e.g., 10 minutes) on the stored verifier; drop if expired.
- Pop the verifier on first use to avoid reuse.
- Do not log verifier/challenge values.

Deliverables:
- Updated OAuth base API (non-breaking), OIDC service, endpoints, and new PKCE utility.

#### Phase 3: Tests
Unit tests (extend `oauth/test/test_oidc.py` or add `oauth/test/test_oidc_pkce.py`):
- Authorization URL contains `code_challenge` and correct method when `USE_PKCE=true`.
- Token POST includes `code_verifier` when `USE_PKCE=true`.
- Works with both `S256` and `plain`.
- `PUBLIC_CLIENT=true` omits `client_secret` in token exchange.
- Verifier is cleared from session after use and TTL enforced.

Integration-style tests with mock OIDC:
- Reuse existing HTTMock patterns in `oauth/test/test_oidc.py` to assert request body/query params; add variants for PKCE.

#### Phase 4: Documentation and Upgrade Notes
- Document new config keys and examples in `docs/` and `CLAUDE.md` Development Tips.
- Note security guidance: prefer `S256`, treat verifiers as secrets, and encourage rotating per request.

### Local Testing Guide

Option A: Local Keycloak with PKCE
1) Start Quay dev env:
   - `make local-dev-up`
2) Run Keycloak (example):
   - `podman run --rm -p 8081:8080 quay.io/keycloak/keycloak:latest start-dev`
   - Create a realm, client (Confidential or Public), set valid redirect URIs: `http://localhost:8080/oauth2/<service>/callback*`.
   - Enable Standard Flow (Authorization Code). For Public client, skip client secret.
3) Quay config (`conf/stack/config.yaml`) example:
```
SOMEOIDC_LOGIN_CONFIG:
  SERVICE_NAME: "Keycloak"
  OIDC_SERVER: "http://localhost:8081/realms/<realm>"
  CLIENT_ID: "quay-ui"
  CLIENT_SECRET: "<secret>"   # omit when PUBLIC_CLIENT: true
  LOGIN_SCOPES: ["openid", "profile", "email"]
  DEBUGGING: true               # allow http for local
  USE_PKCE: true
  PKCE_METHOD: "S256"
  PUBLIC_CLIENT: false          # true if configured as Public in Keycloak
```
4) Restart Quay: `podman restart quay-quay`.
5) Trigger login URL (session-based):
```
CSRF=$(curl -s -c cookies.txt -b cookies.txt http://localhost:8080/csrf_token | jq -r .csrf_token)
curl -s -b cookies.txt -c cookies.txt -H "X-CSRF-Token: $CSRF" -H "Content-Type: application/json" \
  -X POST http://localhost:8080/api/v1/externallogin/someoidc -d '{"kind":"login"}' | jq .auth_url -r
```
6) Open returned `auth_url` in a browser, complete login. Verify successful redirect and Quay session.

Option B: Mock OIDC server for automated tests
- Leverage HTTMock-based unit tests (no external services) to validate PKCE parameters end-to-end.

Validation checks
- Authorization request has `code_challenge` and `code_challenge_method`.
- Token request includes `code_verifier` and succeeds.
- For `PUBLIC_CLIENT=true`, ensure client secret is not transmitted.
- User logged in and visible via `/api/v1/user/` with session cookies.

### Risk/Edge Cases
- Session-wide CSRF token is stable; PKCE verifier is stored per-service to avoid mismatches. Encourage one login attempt at a time per service tab; TTL mitigates reuse.
- Some IdPs may require client auth even with PKCE; keep confidential client behavior by default.
- Ensure `userinfo` disabled flows still work (extract from `id_token`).

### Rollout Plan
- Ship behind per-provider `USE_PKCE` flag (default off).
- Enable in staging with a single provider, monitor logs.
- Enable in production for providers requiring PKCE.

### Estimated Effort
- Code changes: ~200–350 LOC.
- Unit tests: ~150–250 LOC.
- Docs: ~1–2 pages.


