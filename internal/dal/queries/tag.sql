-- name: InsertTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
VALUES (?, ?, ?, ?, ?)
RETURNING id;

-- name: GetActiveTags :many
SELECT id, manifest_id
FROM tag
WHERE repository_id = ? AND name = ? AND lifetime_end_ms IS NULL
ORDER BY id;

-- name: ExpireTagByID :execresult
UPDATE tag SET lifetime_end_ms = ?
WHERE id = ? AND lifetime_end_ms IS NULL;

-- name: TagLifetimeEndExists :one
SELECT EXISTS(
  SELECT 1 FROM tag
  WHERE repository_id = ? AND name = ? AND lifetime_end_ms = ?
);

-- name: DeleteTagsByManifest :exec
DELETE FROM tag WHERE manifest_id = ?;

-- name: GetTagsByRepository :many
SELECT id, name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
FROM tag
WHERE repository_id = ? AND (lifetime_end_ms IS NULL OR lifetime_end_ms > ?) AND hidden = 0;

-- name: GetActiveTagDigest :one
SELECT m.digest
FROM tag t
JOIN manifest m ON t.manifest_id = m.id
WHERE t.repository_id = ? AND t.name = ? AND t.lifetime_end_ms IS NULL;
