-- name: UpsertManifest :one
INSERT INTO manifest (repository_id, digest, media_type_id, manifest_bytes)
VALUES (?, ?, ?, ?)
ON CONFLICT (repository_id, digest) DO UPDATE SET manifest_bytes = excluded.manifest_bytes
RETURNING id;

-- name: GetManifestByDigest :one
SELECT id, repository_id, digest, media_type_id, manifest_bytes
FROM manifest WHERE repository_id = ? AND digest = ?;

-- name: LinkManifestBlob :exec
INSERT OR IGNORE INTO manifestblob (repository_id, manifest_id, blob_id)
VALUES (?, ?, ?);

-- name: LinkManifestChild :exec
INSERT OR IGNORE INTO manifestchild (repository_id, manifest_id, child_manifest_id)
VALUES (?, ?, ?);

-- name: DeleteManifestBlobs :exec
DELETE FROM manifestblob WHERE manifest_id = ?;

-- name: DeleteManifest :exec
DELETE FROM manifest WHERE id = ?;

-- name: CountManifests :one
SELECT COUNT(*) FROM manifest;
