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

-- name: GetRepositoryAccessByNamespaceName :one
SELECT r.id, u.id AS namespace_user_id, u.username AS namespace, r.name, r.visibility_id, v.name AS visibility, r.state
FROM repository r
JOIN "user" u ON r.namespace_user_id = u.id
JOIN visibility v ON r.visibility_id = v.id
WHERE u.username = ? AND r.name = ? AND r.state != 3;

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

-- name: UpdateRepositoryVisibility :execresult
UPDATE repository
SET visibility_id = (SELECT id FROM visibility WHERE visibility.name = @visibility)
WHERE repository.id = @repository_id
  AND state != 3;

-- name: MarkRepositoryDeleted :execresult
UPDATE repository
SET name = @deleted_name, state = 3
WHERE repository.id = @repository_id
  AND state != 3;

-- name: InsertDeletedRepository :one
INSERT INTO deletedrepository (repository_id, marked, original_name)
VALUES (@repository_id, datetime('now'), @original_name)
RETURNING id;

-- name: DeleteStarsByRepository :exec
DELETE FROM star WHERE repository_id = ?;

-- name: ListAllRepositories :many
SELECT u.username AS namespace, r.name
FROM repository r
JOIN "user" u ON r.namespace_user_id = u.id
ORDER BY u.username, r.name;
