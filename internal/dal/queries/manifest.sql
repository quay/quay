-- name: GetManifestByDigest :one
SELECT id, repository_id, digest, media_type_id, manifest_bytes
FROM manifest
WHERE repository_id = ? AND digest = ?;

-- name: UpsertManifest :one
INSERT INTO manifest (repository_id, digest, media_type_id, manifest_bytes, subject, artifact_type, subject_backfilled, artifact_type_backfilled)
VALUES (?, ?, ?, ?, ?, ?, 1, 1)
ON CONFLICT (repository_id, digest) DO UPDATE
  SET manifest_bytes = excluded.manifest_bytes,
      subject = excluded.subject,
      artifact_type = excluded.artifact_type,
      subject_backfilled = 1,
      artifact_type_backfilled = 1
RETURNING id;

-- name: DeleteManifest :exec
DELETE FROM manifest WHERE id = ?;

-- name: LinkManifestBlob :exec
INSERT OR IGNORE INTO manifestblob (repository_id, manifest_id, blob_id)
VALUES (?, ?, ?);

-- name: DeleteManifestBlobs :exec
DELETE FROM manifestblob WHERE manifest_id = ?;

-- name: LinkManifestChild :exec
INSERT OR IGNORE INTO manifestchild (repository_id, manifest_id, child_manifest_id)
VALUES (?, ?, ?);

-- name: DeleteManifestLabels :exec
DELETE FROM manifestlabel WHERE manifest_id = ?;

-- name: DeleteManifestChildren :exec
DELETE FROM manifestchild WHERE manifest_id = ? OR child_manifest_id = ?;

-- name: DeleteManifestSecurityStatus :exec
DELETE FROM manifestsecuritystatus WHERE manifest_id = ?;

-- name: CountManifests :one
SELECT COUNT(*) FROM manifest;

-- name: ManifestExistsByDigest :one
SELECT digest FROM manifest WHERE repository_id = ? AND digest = ?;

-- name: GetManifestContentByDigest :one
SELECT manifest_bytes FROM manifest WHERE digest = ? LIMIT 1;

-- name: ListReferrers :many
SELECT m.digest, mt.name AS media_type, m.artifact_type, length(m.manifest_bytes) AS size, m.manifest_bytes
FROM manifest m
JOIN mediatype mt ON mt.id = m.media_type_id
WHERE m.repository_id = ? AND m.subject = ?;

-- name: ListReferrersByArtifactType :many
SELECT m.digest, mt.name AS media_type, m.artifact_type, length(m.manifest_bytes) AS size, m.manifest_bytes
FROM manifest m
JOIN mediatype mt ON mt.id = m.media_type_id
WHERE m.repository_id = ? AND m.subject = ? AND m.artifact_type = ?;
