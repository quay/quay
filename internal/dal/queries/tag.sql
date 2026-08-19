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

-- name: ExpireActiveTag :execresult
UPDATE tag SET lifetime_end_ms = ?
WHERE repository_id = ? AND name = ? AND lifetime_end_ms IS NULL;

-- name: GetActiveTagLifetimeStart :one
SELECT lifetime_start_ms
FROM tag
WHERE repository_id = ? AND name = ? AND lifetime_end_ms IS NULL
ORDER BY lifetime_start_ms DESC
LIMIT 1;

-- name: TagLifetimeEndExists :one
SELECT EXISTS(
    SELECT 1
    FROM tag
    WHERE repository_id = ? AND name = ? AND lifetime_end_ms = ?
);

-- name: DeleteTagsByManifest :exec
DELETE FROM tag WHERE manifest_id = ?;

-- name: GetTagsByRepository :many
SELECT id, name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
FROM tag
WHERE repository_id = ? AND (lifetime_end_ms IS NULL OR lifetime_end_ms > ?) AND hidden = 0;

-- name: InsertHiddenTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id, hidden)
VALUES (?, ?, ?, ?, ?, 1)
ON CONFLICT (repository_id, name, lifetime_end_ms) DO UPDATE SET manifest_id = excluded.manifest_id
RETURNING id;

-- name: HasNonExpiringTagForManifest :one
-- Returns true if the manifest already has at least one non-expiring tag
-- (lifetime_end_ms IS NULL). Used to skip creating duplicate protection tags.
SELECT EXISTS(
    SELECT 1 FROM tag WHERE manifest_id = ? AND lifetime_end_ms IS NULL
) AS has_tag;

-- name: GetActiveTagDigest :one
SELECT m.digest
FROM tag t
JOIN manifest m ON t.manifest_id = m.id
WHERE t.repository_id = ? AND t.name = ? AND t.lifetime_end_ms IS NULL;
