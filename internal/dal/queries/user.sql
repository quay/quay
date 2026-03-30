-- name: GetUserByUsername :one
SELECT id, uuid, username, password_hash, email, enabled
FROM "user"
WHERE username = ? AND organization = 0 AND robot = 0;

-- name: CreateUser :one
INSERT INTO "user" (uuid, username, password_hash, email, verified,
  organization, robot, invoice_email, invalid_login_attempts,
  last_invalid_login, removed_tag_expiration_s, enabled, creation_date)
VALUES (?, ?, ?, ?, 1, 0, 0, 0, 0, datetime('now'), 1209600, 1, datetime('now'))
RETURNING id;
