-- name: UpsertTag :one
-- KNOWN LIMITATION: ON CONFLICT uses lifetime_end_ms which is nullable.
-- NULL != NULL in SQL, so active tags (lifetime_end_ms IS NULL) never conflict.
-- This inserts duplicates instead of updating. Proper fix requires a partial
-- unique index: CREATE UNIQUE INDEX ON tag (repository_id, name) WHERE lifetime_end_ms IS NULL.
-- Until then, callers should expire the old tag before inserting a new one.
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT (repository_id, name, lifetime_end_ms) DO UPDATE SET manifest_id = excluded.manifest_id
RETURNING id;

-- name: GetTagsByRepository :many
SELECT id, name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
FROM tag
WHERE repository_id = ? AND (lifetime_end_ms IS NULL OR lifetime_end_ms > ?) AND hidden = 0;
