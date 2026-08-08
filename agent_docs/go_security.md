# Go Auth/Authz Security Review Checklist

Security review checklist for Go code that touches authentication,
authorization, access control, or configuration migration. Apply this
checklist before submitting or reviewing any Go PR that modifies files
under `internal/auth/`, `internal/repository/dal/`, `internal/registry/`,
`internal/config/`, or `internal/api/`.

## 1. Authorization Completeness

Every endpoint that authenticates a request must also authorize it.
Authentication alone (knowing *who* the caller is) is not sufficient;
the code must verify the caller has permission to perform the specific
action on the specific resource.

**What to check:**

- Every handler or middleware that calls `Authenticate()` must also call
  a resource-level authorization function (`CanPullRepository`,
  `CanPushRepository`, `CanAdminRepository`, `CanCreateRepository`).
- If a new endpoint is added that uses `BasicAuthenticator` or any other
  authentication mechanism, verify that the handler also performs an
  authorization check before returning data or performing mutations.
- If authorization is delegated to a helper (e.g., `authorize()` in
  `internal/registry/referrers.go`), trace the helper to confirm it
  calls the authorizer, not just the authenticator.

**Bad pattern (authentication without authorization):**

```go
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    result := h.authenticator.Authenticate(r)
    if !result.Authenticated {
        http.Error(w, "unauthorized", 401)
        return
    }
    // BUG: authenticated but never authorized -- any authenticated
    // user can access any resource.
    data := h.store.GetData(r.Context(), name)
    json.NewEncoder(w).Encode(data)
}
```

**Correct pattern:**

```go
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    result := h.authenticator.Authenticate(r)
    if !result.Authenticated {
        http.Error(w, "unauthorized", 401)
        return
    }
    allowed, err := h.authorizer.CanPullRepository(
        r.Context(), &result.Principal, repo,
    )
    if err != nil || !allowed {
        http.Error(w, "forbidden", 403)
        return
    }
    data := h.store.GetData(r.Context(), name)
    json.NewEncoder(w).Encode(data)
}
```

**Reference implementation:** `internal/registry/referrers.go` --
`authorize()` authenticates, then calls `canPullRepository()` which
delegates to `authorizer.CanPullRepository()`.

## 2. Entity State Validation

Access-control functions must check lifecycle state fields before
granting access. Deleted, disabled, or otherwise inactive entities must
not be accessible, even if they were public before deletion.

**What to check:**

- `CanPullRepository` must check `repo.State != StateMarkedForDeletion`
  **before** the public-visibility fast path. A deleted public repo must
  not be pullable.
- `CanPullRepository` and `CanPushRepository` must check
  `repo.NamespaceEnabled` before granting access. A disabled namespace
  blocks all repository operations.
- `CanPushRepository` must validate `repo.State` against the allowed
  write states (`StateNormal`, `StateMirror`, `StateOrgMirror`) and
  reject all others.
- Any new access-control function must validate entity state. If the
  entity has a lifecycle state field, check it.

**Bad pattern (missing state check before public fast path):**

```go
func (a *Authorizer) CanPullRepository(ctx context.Context,
    principal *auth.Principal, repo *Repository) (bool, error) {
    if repo.Visibility == VisibilityPublic {
        return true, nil  // BUG: deleted public repos are still pullable
    }
    // ...
}
```

**Correct pattern:**

```go
func (a *Authorizer) CanPullRepository(ctx context.Context,
    principal *auth.Principal, repo *Repository) (bool, error) {
    if !repo.NamespaceEnabled {
        return false, nil
    }
    if repo.State == StateMarkedForDeletion {
        return false, nil
    }
    if repo.Visibility == VisibilityPublic {
        return true, nil
    }
    // ...
}
```

**Reference implementation:** `internal/repository/dal/authz.go` --
`CanPullRepository` checks `NamespaceEnabled` and
`StateMarkedForDeletion` before the public-visibility branch.

## 3. Timing-Safe Authentication

All authentication verification paths must perform equivalent work to
prevent timing side-channels. An attacker who can distinguish "user does
not exist" from "wrong password" by measuring response time can enumerate
valid accounts.

**What to check:**

- Every early-return failure branch in a credential verifier (invalid
  format, missing entity, disabled owner) must call a dummy operation
  that matches the cost of the success path.
- The dummy operation should use the same cryptographic primitives as
  the real verification (e.g., `encryptedfield.Decrypt` +
  `subtle.ConstantTimeCompare`).
- Use `crypto/subtle.ConstantTimeCompare` for all secret comparisons,
  never `==` or `bytes.Equal`.
- Verify that authentication result types do not leak which step failed
  to the caller. The external response should be the same regardless of
  whether the user was not found, the token was wrong, or the owner was
  disabled.

**Bad pattern (timing side-channel):**

```go
func (v *tokenVerifier) Verify(ctx context.Context,
    creds Credentials) Result {
    owner, ok := parseUsername(creds.Username)
    if !ok {
        return failedResult(creds.Username)  // BUG: fast return, no
                                             // decrypt -- timing oracle
    }
    entity, ok := v.lookupEntity(ctx, creds.Username)
    if !ok {
        return failedResult(creds.Username)  // BUG: fast return
    }
    // ... decrypt and compare ...
}
```

**Correct pattern:**

```go
func (v *tokenVerifier) Verify(ctx context.Context,
    creds Credentials) Result {
    owner, ok := parseUsername(creds.Username)
    if !ok {
        v.dummySecretMatch(creds)  // constant-time filler
        return failedResult(creds.Username)
    }
    entity, ok := v.lookupEntity(ctx, creds.Username)
    if !ok {
        v.dummySecretMatch(creds)  // constant-time filler
        return failedResult(creds.Username)
    }
    if !v.ownerEnabled(ctx, owner) {
        v.dummySecretMatch(creds)  // constant-time filler
        return failedResult(creds.Username)
    }
    if !v.secretMatches(ctx, entity.ID, creds) {
        return failedResult(creds.Username)
    }
    // ... success ...
}
```

**Reference implementation:** `internal/auth/robot_static_token.go` --
`staticRobotTokenVerifier.Verify()` calls `dummySecretMatch()` on every
early-return branch. `dummySecretMatch` performs the same decrypt +
constant-time compare as the real path.

## 4. Config Migration Completeness

When Go code reads or copies runtime configuration, all
security-sensitive fields must be preserved. Dropping a field during
migration or config construction silently disables a security control.

**What to check:**

- When constructing a config struct (e.g., `ReferrersConfig`,
  `DatabaseVerifierConfig`, `AuthorizerConfig`), verify that all
  security-sensitive source fields are mapped to the destination.
  Security-sensitive fields include:
  - `SUPER_USERS` and `FEATURE_SUPERUSERS_FULL_ACCESS`
  - `ROBOTS_DISALLOW` and `ROBOTS_WHITELIST`
  - `DATABASE_SECRET_KEY`
  - Feature flags that gate access control (`FEATURE_SUPER_USERS`,
    `FEATURE_ANONYMOUS_ACCESS`)
- When adding a new handler that consumes config, compare the config
  struct fields against the source (`internal/config/` types) to ensure
  nothing is dropped.
- Write test assertions that verify security-sensitive config fields
  are present and have the expected values after construction. A test
  like `TestSchemaFieldCoverage` in `internal/config/schema_test.go`
  catches drift between Python and Go config schemas -- apply the same
  pattern to runtime config construction.

**Bad pattern (dropped security fields):**

```go
func writeRuntimeConfig(src *config.Config) *RuntimeConfig {
    return &RuntimeConfig{
        Hostname: src.ServerHostname,
        DBURI:    src.DBURI,
        // BUG: SUPER_USERS, FEATURE_SUPERUSERS_FULL_ACCESS, and
        // ROBOTS_DISALLOW are silently dropped -- superuser
        // protections are disabled in the Go runtime.
    }
}
```

**Correct pattern:**

```go
func writeRuntimeConfig(src *config.Config) *RuntimeConfig {
    return &RuntimeConfig{
        Hostname:             src.ServerHostname,
        DBURI:                src.DBURI,
        SuperUsers:           src.SuperUsers,
        SuperUsersFullAccess: derefBool(src.FeatureSuperUsersFullAccess),
        RobotsDisallow:       src.RobotsDisallow,
        RobotsWhitelist:      src.RobotsWhitelist,
    }
}
```

**Reference implementation:** `internal/registry/referrers.go` --
`NewReferrersHandler` maps `SuperUsers`, `SuperUsersFullAccess`,
`RobotsDisallow`, `RobotsWhitelist`, and `DatabaseSecretKey` from
`ReferrersConfig` to the authenticator and authorizer constructors.

## 5. Defense-in-Depth SQL

Authorization SQL queries should enforce state and enablement checks at
the database level, even when the Go application layer has pre-checks.
This prevents a logic error in the Go layer from silently granting
access.

**What to check:**

- Authorization queries (`UserCanPullRepository`,
  `UserCanPushRepository`, `UserCanCreateRepositoryInNamespace`) must
  include `AND ns.enabled = 1` in every branch that joins the namespace
  user table.
- The `GetRepositoryAccessByNamespaceName` query should exclude
  repositories in terminal states (e.g., `AND r.state != 3` to exclude
  `StateMarkedForDeletion`).
- When adding a new authorization query, include state and enablement
  checks in the SQL `WHERE` clause, not just in the Go caller. Both
  layers should enforce the same invariants.
- When reviewing SQL, check every `UNION ALL` branch independently.
  A missing `AND ns.enabled = 1` in one branch creates a bypass even
  if other branches have it.

**Bad pattern (missing namespace check in SQL):**

```sql
-- name: UserCanPullRepository :one
SELECT EXISTS(
  SELECT 1
  FROM repository r
  JOIN "user" ns ON r.namespace_user_id = ns.id
  WHERE r.id = @repository_id
    AND ns.username = @username
    -- BUG: no ns.enabled check -- disabled namespace owners
    -- can still pull via this branch

  UNION ALL

  SELECT 1
  FROM repositorypermission rp
  -- ...
);
```

**Correct pattern:**

```sql
-- name: UserCanPullRepository :one
SELECT EXISTS(
  SELECT 1
  FROM repository r
  JOIN "user" ns ON r.namespace_user_id = ns.id
  WHERE r.id = @repository_id
    AND ns.username = @username
    AND ns.enabled = 1

  UNION ALL

  SELECT 1
  FROM repositorypermission rp
  -- ... (also includes ns.enabled checks where applicable)
);
```

**Reference implementation:** `internal/dal/queries/repository.sql` --
`UserCanPullRepository`, `UserCanPushRepository`, and
`UserCanCreateRepositoryInNamespace` all include `AND ns.enabled = 1`
in their namespace-owner branches.

## Review Procedure

When reviewing a Go PR that touches auth, authz, or config code:

1. For each endpoint or handler: trace the request path from HTTP entry
   to data access. Confirm authentication AND authorization are both
   present (checklist item 1).
2. For each access-control function: verify all entity state fields are
   checked before any fast-path return (checklist item 2).
3. For each credential verifier: map every early-return branch and
   confirm each performs equivalent-cost dummy work (checklist item 3).
4. For each config construction or migration: diff the source config
   type against the destination to identify dropped fields. Flag any
   missing security-sensitive field (checklist item 4).
5. For each new or modified SQL query in `internal/dal/queries/`: verify
   `ns.enabled` and state checks are present in every `UNION ALL`
   branch (checklist item 5).

## Key Files

| File | Role |
|------|------|
| `internal/auth/verifier.go` | `Verifier` interface |
| `internal/auth/robot_static_token.go` | Robot token verification with timing-safe patterns |
| `internal/auth/basic.go` | Basic auth middleware |
| `internal/auth/database_verifier.go` | Database credential verifier dispatcher |
| `internal/repository/dal/authz.go` | `CanPullRepository`, `CanPushRepository`, `CanAdminRepository` |
| `internal/repository/types.go` | Repository state and visibility constants |
| `internal/registry/distribution/auth.go` | Distribution/v3 access controller |
| `internal/registry/referrers.go` | OCI referrers endpoint with auth + authz |
| `internal/config/features.go` | Feature flag struct |
| `internal/config/auth.go` | Auth config (SUPER_USERS, ROBOTS_DISALLOW) |
| `internal/dal/queries/repository.sql` | Authorization SQL queries |
