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
WHERE repository_id = ? AND lifetime_end_ms IS NULL AND hidden = 0;

-- name: InsertHiddenTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id, hidden)
VALUES (?, ?, ?, ?, ?, 1)
ON CONFLICT (repository_id, name, lifetime_end_ms) DO UPDATE SET manifest_id = excluded.manifest_id
RETURNING id;

-- name: InsertHiddenExpiringTag :one
-- Hidden $temp- tag with an explicit lifetime_end_ms. Matches Python
-- create_temporary_tag_if_necessary(expiration_sec, skip_expiration=False)
-- used for digest-only manifest PUTs (PUSH_TEMP_TAG_EXPIRATION_SEC).
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id, hidden)
VALUES (?, ?, ?, ?, ?, ?, 1)
RETURNING id;

-- name: HasProtectingTagForManifest :one
-- True if the manifest already has a tag that never expires or expires at or
-- after the requested epoch-ms. Used to skip a new $temp- when an existing
-- tag already covers the requested window (named tag, referrer, or a
-- still-valid temp tag).
SELECT EXISTS(
    SELECT 1 FROM tag
    WHERE manifest_id = ?
      AND (lifetime_end_ms IS NULL OR lifetime_end_ms >= ?)
) AS has_tag;

-- name: ExtendTempTag :execrows
-- Pushes the expiry of a manifest's existing temp tag(s) forward so a
-- re-push renews protection without inserting another row.
UPDATE tag SET lifetime_end_ms = ?
WHERE manifest_id = ? AND hidden = 1 AND lifetime_end_ms IS NOT NULL AND lifetime_end_ms < ?;

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
