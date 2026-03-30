-- name: UpsertTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT (repository_id, name, lifetime_end_ms) DO UPDATE SET manifest_id = excluded.manifest_id
RETURNING id;

-- name: GetTagsByRepository :many
SELECT id, name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
FROM tag
WHERE repository_id = ? AND lifetime_end_ms IS NULL;
