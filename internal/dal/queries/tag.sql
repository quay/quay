-- name: InsertTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
VALUES (?, ?, ?, ?, ?)
RETURNING id;

-- name: GetActiveTag :one
SELECT id, manifest_id, lifetime_start_ms
FROM tag
WHERE repository_id = ? AND name = ? AND lifetime_end_ms IS NULL
ORDER BY lifetime_start_ms DESC, id DESC
LIMIT 1;

-- name: ExpireTagByID :execresult
UPDATE tag SET lifetime_end_ms = ?
WHERE id = ? AND lifetime_end_ms IS NULL;

-- name: DeleteTagsByManifest :exec
DELETE FROM tag WHERE manifest_id = ?;

-- name: GetTagsByRepository :many
SELECT id, name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
FROM tag
WHERE repository_id = ? AND (lifetime_end_ms IS NULL OR lifetime_end_ms > ?) AND hidden = 0;

-- name: InsertHiddenTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id, hidden)
VALUES (?, ?, ?, ?, ?, 1)
ON CONFLICT (repository_id, name) WHERE lifetime_end_ms IS NULL
DO UPDATE SET manifest_id = excluded.manifest_id
RETURNING id;

-- name: GetActiveTagDigest :one
SELECT m.digest
FROM tag t
JOIN manifest m ON t.manifest_id = m.id
WHERE t.repository_id = ? AND t.name = ? AND t.lifetime_end_ms IS NULL;
