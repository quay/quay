-- name: FindExpiredTags :many
-- Returns tags whose soft-delete grace period has elapsed.
-- A tag is expired when lifetime_end_ms is set AND enough time has passed
-- per the owning namespace's removed_tag_expiration_s setting.
SELECT t.id, t.name, t.repository_id, t.manifest_id
FROM tag t
JOIN repository r ON t.repository_id = r.id
JOIN "user" u ON r.namespace_user_id = u.id
WHERE t.lifetime_end_ms IS NOT NULL
  AND t.lifetime_end_ms <= (
    (strftime('%s', 'now') * 1000) - (u.removed_tag_expiration_s * 1000)
  );

-- name: FindOrphanedManifests :many
-- Returns manifests with no tags at all (neither live nor within grace period),
-- not referenced as a child by any manifest list (globally, not repo-scoped),
-- and not a subject target of any other manifest (OCI referrers, globally).
-- IMPORTANT: This checks for ANY tag, including expired-but-within-grace-period
-- tags. This is intentional. Phase 1 runs first and deletes only tags past their
-- grace period. Any tag still present here (live or within grace) must protect
-- the manifest. Do NOT add "AND lifetime_end_ms IS NULL" as that would allow
-- manifests to be deleted while their tags are still recoverable.
SELECT m.id, m.repository_id, m.digest
FROM manifest m
WHERE NOT EXISTS (
    SELECT 1 FROM tag t
    WHERE t.manifest_id = m.id
  )
  AND NOT EXISTS (
    SELECT 1 FROM manifestchild mc
    WHERE mc.child_manifest_id = m.id
  )
  AND NOT EXISTS (
    SELECT 1 FROM manifest m2
    WHERE m2.subject = m.digest
  );

-- name: DeleteExpiredTag :exec
DELETE FROM tag WHERE id = ?;

-- name: FindOrphanedManifestsByRepo :many
-- Same as FindOrphanedManifests but scoped to a single repository.
SELECT m.id, m.repository_id, m.digest
FROM manifest m
WHERE m.repository_id = ?
  AND NOT EXISTS (
    SELECT 1 FROM tag t
    WHERE t.manifest_id = m.id
  )
  AND NOT EXISTS (
    SELECT 1 FROM manifestchild mc
    WHERE mc.child_manifest_id = m.id
  )
  AND NOT EXISTS (
    SELECT 1 FROM manifest m2
    WHERE m2.subject = m.digest
  );

-- name: ListRepositoryIDs :many
SELECT id FROM repository WHERE state != 3;

-- name: DeleteTagNotifications :exec
DELETE FROM tagnotificationsuccess WHERE tag_id = ?;

-- name: DeleteImageStoragePlacements :exec
DELETE FROM imagestorageplacement WHERE storage_id = ?;

-- name: DeleteImageStorageSignatures :exec
DELETE FROM imagestoragesignature WHERE storage_id = ?;

-- name: DeleteUploadedBlobsByBlobID :exec
DELETE FROM uploadedblob WHERE blob_id = ?;

-- name: CountManifestBlobRefs :one
SELECT COUNT(*) FROM manifestblob WHERE blob_id = ?;

-- name: CountActiveUploadedBlobRefs :one
SELECT COUNT(*) FROM uploadedblob WHERE blob_id = ? AND expires_at > datetime('now');

-- name: CountBlobsByChecksum :one
SELECT COUNT(*) FROM imagestorage WHERE content_checksum = ?;
