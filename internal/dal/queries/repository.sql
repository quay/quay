-- name: GetRepositoryByName :one
SELECT id, namespace_user_id, name, visibility_id, kind_id, state
FROM repository
WHERE namespace_user_id = ? AND name = ?;

-- name: GetOrCreateRepository :one
INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, badge_token, state)
VALUES (?, ?, ?, ?, ?, 0)
ON CONFLICT (namespace_user_id, name) DO UPDATE SET name = excluded.name
RETURNING id;

-- name: CountRepositories :one
SELECT COUNT(*) FROM repository;

-- name: GetRepositoryByNamespaceName :one
SELECT r.id FROM repository r
JOIN "user" u ON r.namespace_user_id = u.id
WHERE u.username = ? AND r.name = ?;

-- name: RepositoryIsPublicByNamespaceName :one
SELECT EXISTS(
  SELECT 1
  FROM repository r
  JOIN "user" u ON r.namespace_user_id = u.id
  JOIN visibility v ON r.visibility_id = v.id
  WHERE u.username = ?
    AND r.name = ?
    AND v.name = 'public'
    AND r.state != 3
);

-- name: ListAllRepositories :many
SELECT u.username AS namespace, r.name
FROM repository r
JOIN "user" u ON r.namespace_user_id = u.id
ORDER BY u.username, r.name;
