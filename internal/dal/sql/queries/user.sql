-- name: CreateUser :one
INSERT INTO user (uuid, username, password_hash, email, verified_email,
  organization, robot, enabled, removed_tag_expiration_s,
  invalid_login_attempts, creation_date)
VALUES (?, ?, ?, ?, 1, 0, 0, 1, 1209600, 0, datetime('now'))
RETURNING id;

-- name: GetUserByUsername :one
SELECT id, uuid, username, password_hash, email, enabled
FROM user WHERE username = ? AND organization = 0 AND robot = 0;
