-- name: UpsertRepository :one
INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
VALUES (?, ?, ?, ?, 0)
ON CONFLICT (namespace_user_id, name) DO UPDATE SET name = excluded.name
RETURNING id;

-- name: GetRepositoryByName :one
SELECT id, namespace_user_id, name, visibility_id, kind_id, state
FROM repository WHERE namespace_user_id = ? AND name = ?;

-- name: CountRepositories :one
SELECT COUNT(*) FROM repository;
