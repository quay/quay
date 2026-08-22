# Auth Backend and Mechanism Inventory

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Capture authentication provider/backend parity requirements for the Go rewrite.

Primary source anchors:
- `data/users/`
- `auth/`

## 2. Identity provider backends

Required backend parity list:
1. Database
2. LDAP
3. External JWT
4. Keystone v2/v3
5. AppToken
6. OIDC

For each backend, define:
- Go library/runtime mapping
- configuration compatibility requirements
- user-linking/team-sync behavior
- failure and fallback behavior

## 3. Auth mechanisms to preserve

1. Basic auth
2. Session/cookie auth
3. OAuth flows
4. SSO JWT (`ssojwt`) flow
5. Signed grant flows
6. Credential helper/service flows
7. Federated robot auth (`federated`) flow
8. Registry JWT token flow (`process_registry_jwt_auth`)

## 4. Migration strategy

- Separate backend-provider parity from route-level auth mode parity.
- Keep provider adapters behind a shared `identity.Provider` interface.
- Build provider conformance tests with real or simulated providers.

## 5. Implementation architecture (two auth pipelines)

Pipeline A: `ValidateResult`-style mechanisms
- basic
- cookie/session
- oauth
- ssojwt
- signed_grant
- credentials
- federated

Pipeline B: registry JWT identity-context path
- `process_registry_jwt_auth`
- this path builds signed identity context directly and should be implemented as a distinct middleware chain.

Design rule:
- Do not force both pipelines through one middleware abstraction if it changes behavior/identity semantics.

## 6. Test requirements

- Backend login/refresh/logout parity tests.
- Federated identity linking tests.
- Team synchronization behavior tests.
- Negative-path tests (provider outage, bad claims, mapping conflicts).
- Mechanism parity tests for all 8 auth mechanisms (including `ssojwt`, `federated`, and registry JWT scope handling).
- Separate test suites for pipeline-A vs pipeline-B behavior and context propagation.

## 7. Exit criteria (gate G14)

- All six backends mapped with owner and Go library decisions.
- All eight auth mechanisms mapped to middleware/validator owners with explicit parity test IDs.
- Conformance tests pass for enabled backends.
- Auth regression dashboard includes per-backend failure metrics.
