-- name: GetUserByUsername :one
SELECT id, uuid, username, password_hash, email, enabled
FROM "user"
WHERE username = ? AND organization = 0 AND robot = 0;

-- name: CreateAdminUser :one
INSERT INTO "user" (uuid, username, password_hash, email, verified,
  organization, robot, invoice_email, invalid_login_attempts,
  last_invalid_login, removed_tag_expiration_s, enabled, creation_date)
VALUES (?, ?, ?, ?, 1, 0, 0, 0, 0, datetime('now'), 1209600, 1, datetime('now'))
RETURNING id;

-- name: EnsureUser :one
-- Creates a synthetic user row for namespace resolution. Mirror-registry
-- namespaces map 1:1 to user rows; these are not real login accounts.
INSERT INTO "user" (username, email, verified, organization, robot,
  invoice_email, invalid_login_attempts, last_invalid_login,
  removed_tag_expiration_s, enabled)
VALUES (@username, @username || '@namespace.local', 1, 0, 0, 0, 0, datetime('now'), 1209600, 1)
ON CONFLICT (username) DO UPDATE SET username = excluded.username
RETURNING id;

-- name: CountUsers :one
SELECT count(*) FROM "user" WHERE organization = 0 AND robot = 0;
