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
  AND repository.state != 3
  AND EXISTS (SELECT 1 FROM visibility WHERE visibility.name = @visibility);

-- name: MarkRepositoryDeleted :execresult
-- MarkRepositoryDeleted uses repository.state = 3 as the deleted state; state != 3 limits this to active repositories.
UPDATE repository
SET name = @deleted_name, state = 3
WHERE repository.id = @repository_id
  AND state != 3;

-- name: InsertDeletedRepository :one
INSERT INTO deletedrepository (repository_id, marked, original_name)
VALUES (@repository_id, datetime('now'), @original_name)
RETURNING id;

-- name: InsertRepositoryGCQueueItem :one
INSERT INTO queueitem (queue_name, body, available_after, available, retries_remaining, state_id)
VALUES (@queue_name, @body, datetime('now'), @available, @retries_remaining, @state_id)
RETURNING id;

-- name: UpdateDeletedRepositoryQueueID :exec
UPDATE deletedrepository
SET queue_id = @queue_id
WHERE id = @id;

-- name: DeleteStarsByRepository :exec
DELETE FROM star WHERE repository_id = ?;

-- name: UserCanAdminRepository :one
SELECT EXISTS(
  SELECT 1
  FROM repository r
  JOIN "user" ns ON r.namespace_user_id = ns.id
  WHERE r.id = @repository_id
    AND ns.username = @username

  UNION ALL

  SELECT 1
  FROM repositorypermission rp
  JOIN role ro ON rp.role_id = ro.id
  WHERE rp.repository_id = @repository_id
    AND rp.user_id = @user_id
    AND ro.name = 'admin'

  UNION ALL

  SELECT 1
  FROM repositorypermission rp
  JOIN role ro ON rp.role_id = ro.id
  JOIN teammember tm ON rp.team_id = tm.team_id
  WHERE rp.repository_id = @repository_id
    AND tm.user_id = @user_id
    AND ro.name = 'admin'

  UNION ALL

  SELECT 1
  FROM repository r
  JOIN team t ON t.organization_id = r.namespace_user_id
  JOIN teamrole tr ON t.role_id = tr.id
  JOIN teammember tm ON tm.team_id = t.id
  WHERE r.id = @repository_id
    AND tm.user_id = @user_id
    AND tr.name = 'admin'
);

-- name: ListAllRepositories :many
SELECT u.username AS namespace, r.name
FROM repository r
JOIN "user" u ON r.namespace_user_id = u.id
ORDER BY u.username, r.name;
