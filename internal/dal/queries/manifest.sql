-- name: GetManifestByDigest :one
SELECT id, repository_id, digest, media_type_id, manifest_bytes
FROM manifest
WHERE repository_id = ? AND digest = ?;

-- name: UpsertManifest :one
INSERT INTO manifest (repository_id, digest, media_type_id, manifest_bytes)
VALUES (?, ?, ?, ?)
ON CONFLICT (repository_id, digest) DO UPDATE SET manifest_bytes = excluded.manifest_bytes
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
