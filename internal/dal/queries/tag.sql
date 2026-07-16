-- name: InsertTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
VALUES (?, ?, ?, ?, ?)
RETURNING id;

-- name: GetActiveTag :one
-- Tag IDs preserve insertion order even when the wall clock moves backward.
SELECT id, manifest_id, lifetime_start_ms
FROM tag
WHERE repository_id = ? AND name = ? AND lifetime_end_ms IS NULL
ORDER BY id DESC
LIMIT 1;

-- name: GetLatestTagInterval :one
-- Tag IDs preserve insertion order even when the wall clock moves backward.
SELECT lifetime_start_ms, lifetime_end_ms
FROM tag
WHERE repository_id = ? AND name = ?
ORDER BY id DESC
LIMIT 1;

-- name: ExpireTagByID :execresult
UPDATE tag SET lifetime_end_ms = ?
WHERE id = ? AND lifetime_end_ms IS NULL;

-- name: DeleteTagsByManifest :exec
DELETE FROM tag WHERE manifest_id = ?;

-- name: GetTagsByRepository :many
WITH ranked_tags AS (
  SELECT name, lifetime_start_ms, lifetime_end_ms,
         row_number() OVER (
           PARTITION BY repository_id, name
           ORDER BY id DESC
         ) AS row_num
  FROM tag
  WHERE repository_id = ? AND hidden = 0
)
SELECT name
FROM ranked_tags
WHERE row_num = 1
  AND (lifetime_end_ms IS NULL OR (lifetime_start_ms <= ? AND lifetime_end_ms > ?))
ORDER BY name;

-- name: InsertHiddenTag :one
INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id, hidden)
VALUES (?, ?, ?, ?, ?, 1)
ON CONFLICT (repository_id, name) WHERE lifetime_end_ms IS NULL
DO UPDATE SET manifest_id = excluded.manifest_id
RETURNING id;

-- name: GetLiveTagDigest :one
WITH latest_tag AS (
  SELECT t.manifest_id, t.lifetime_start_ms, t.lifetime_end_ms
  FROM tag t
  WHERE t.repository_id = ? AND t.name = ?
  ORDER BY t.id DESC
  LIMIT 1
)
SELECT m.digest
FROM latest_tag t
JOIN manifest m ON t.manifest_id = m.id
WHERE t.lifetime_end_ms IS NULL
   OR (t.lifetime_start_ms <= ? AND t.lifetime_end_ms > ?);
