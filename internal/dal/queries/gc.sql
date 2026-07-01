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
-- Phase 1 deletes expired-past-grace tags first, so any remaining tag protects
-- the manifest.
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
