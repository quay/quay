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

-- Repository purge (PROJQUAY-13202). The repository API marks a repository as
-- deleted (state = 3, renamed to a UUID, deletedrepository marker plus a
-- queueitem) exactly like Quay's mark_repository_for_deletion. Quay drains
-- that queue with repositorygcworker; the mirror registry purges marked
-- repositories inside its GC cycle instead. Deletes run child tables first so
-- SQLite foreign keys (PRAGMA foreign_keys=1) are satisfied.

-- name: FindMarkedRepositories :many
SELECT r.id, d.id AS marker_id, d.queue_id
FROM repository r
LEFT JOIN deletedrepository d ON d.repository_id = r.id
WHERE r.state = 3
ORDER BY r.id;

-- name: CountManifestsByRepository :one
SELECT COUNT(*) FROM manifest WHERE repository_id = ?;

-- name: CountTagsByRepository :one
SELECT COUNT(*) FROM tag WHERE repository_id = ?;

-- name: DeleteTagNotificationsByRepository :exec
DELETE FROM tagnotificationsuccess
WHERE tag_id IN (SELECT id FROM tag WHERE repository_id = ?);

-- name: DeleteTagsByRepository :exec
DELETE FROM tag WHERE repository_id = ?;

-- name: DeleteManifestLabelsByRepository :exec
DELETE FROM manifestlabel WHERE repository_id = ?;

-- name: DeleteManifestChildrenByRepository :exec
DELETE FROM manifestchild WHERE repository_id = ?;

-- name: DeleteManifestBlobsByRepository :exec
DELETE FROM manifestblob WHERE repository_id = ?;

-- name: DeleteManifestSecurityStatusByRepository :exec
DELETE FROM manifestsecuritystatus WHERE repository_id = ?;

-- name: DeleteManifestPullStatisticsByRepository :exec
DELETE FROM manifestpullstatistics WHERE repository_id = ?;

-- name: DeleteTagPullStatisticsByRepository :exec
DELETE FROM tagpullstatistics WHERE repository_id = ?;

-- name: DeleteManifestsByRepository :exec
DELETE FROM manifest WHERE repository_id = ?;

-- name: DeleteUploadedBlobsByRepository :exec
DELETE FROM uploadedblob WHERE repository_id = ?;

-- name: DeleteBlobUploadsByRepository :exec
DELETE FROM blobupload WHERE repository_id = ?;

-- name: DeleteRepositoryBuildsByRepository :exec
DELETE FROM repositorybuild WHERE repository_id = ?;

-- name: DeleteRepositoryBuildTriggersByRepository :exec
DELETE FROM repositorybuildtrigger WHERE repository_id = ?;

-- name: DeleteAccessTokensByRepository :exec
DELETE FROM accesstoken WHERE repository_id = ?;

-- name: DeleteRepoMirrorConfigByRepository :exec
DELETE FROM repomirrorconfig WHERE repository_id = ?;

-- name: DeleteRepoMirrorRulesByRepository :exec
DELETE FROM repomirrorrule WHERE repository_id = ?;

-- name: DeleteOrgMirrorRepositoriesByRepository :exec
DELETE FROM orgmirrorrepository WHERE repository_id = ?;

-- name: DeleteApprTagsByRepository :exec
DELETE FROM apprtag WHERE repository_id = ?;

-- name: DeleteRepositoryPermissionsByRepository :exec
DELETE FROM repositorypermission WHERE repository_id = ?;

-- name: DeleteRepositoryNotificationsByRepository :exec
DELETE FROM repositorynotification WHERE repository_id = ?;

-- name: DeleteRepositoryActionCountsByRepository :exec
DELETE FROM repositoryactioncount WHERE repository_id = ?;

-- name: DeleteRepositoryAuthorizedEmailsByRepository :exec
DELETE FROM repositoryauthorizedemail WHERE repository_id = ?;

-- name: DeleteRepositoryAutoPrunePoliciesByRepository :exec
DELETE FROM repositoryautoprunepolicy WHERE repository_id = ?;

-- name: DeleteRepositoryImmutabilityPoliciesByRepository :exec
DELETE FROM repositoryimmutabilitypolicy WHERE repository_id = ?;

-- name: DeleteRepositorySearchScoresByRepository :exec
DELETE FROM repositorysearchscore WHERE repository_id = ?;

-- name: DeleteQuotaRepositorySizesByRepository :exec
DELETE FROM quotarepositorysize WHERE repository_id = ?;

-- name: DeleteStarsByRepositoryForPurge :exec
DELETE FROM star WHERE repository_id = ?;

-- name: DeleteDeletedRepositoryMarkers :exec
DELETE FROM deletedrepository WHERE repository_id = ?;

-- name: DeleteQueueItem :exec
DELETE FROM queueitem WHERE id = ?;

-- name: DeleteRepository :exec
DELETE FROM repository WHERE id = ? AND state = 3;
