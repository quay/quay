-- name: GetBlobByChecksum :one
SELECT id FROM imagestorage WHERE content_checksum = ?;

-- name: InsertBlob :one
INSERT INTO imagestorage (uuid, content_checksum, image_size, uploading, cas_path)
VALUES (?, ?, ?, 0, 1)
ON CONFLICT (uuid) DO UPDATE SET content_checksum = excluded.content_checksum
RETURNING id;

-- name: FindOrphanedBlobs :many
SELECT s.id, s.content_checksum, s.uuid, s.image_size
FROM imagestorage s
WHERE s.uploading = 0
  AND s.id NOT IN (SELECT blob_id FROM manifestblob)
  AND s.id NOT IN (
    SELECT blob_id FROM uploadedblob WHERE expires_at > datetime('now')
  );

-- name: DeleteImageStorage :exec
DELETE FROM imagestorage WHERE id = ?;

-- name: TotalStorageBytes :one
SELECT COALESCE(SUM(image_size), 0) FROM imagestorage WHERE uploading = 0;

-- name: InsertUploadedBlob :exec
INSERT OR IGNORE INTO uploadedblob (repository_id, blob_id, uploaded_at, expires_at)
VALUES (?, ?, datetime('now'), datetime('now', '+1 hour'));

-- name: CleanExpiredUploadedBlobs :exec
DELETE FROM uploadedblob WHERE expires_at < datetime('now');

-- name: BlobLinkedToRepo :one
-- Matches Python's get_repository_blob_by_digest: checks both ManifestBlob
-- and UploadedBlob (for recently pushed blobs not yet referenced by a manifest).
SELECT 1 FROM imagestorage s
WHERE s.content_checksum = ? AND (
  EXISTS (SELECT 1 FROM manifestblob mb WHERE mb.blob_id = s.id AND mb.repository_id = ?)
  OR EXISTS (SELECT 1 FROM uploadedblob ub WHERE ub.blob_id = s.id AND ub.repository_id = ? AND ub.expires_at > datetime('now'))
);
