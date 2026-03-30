-- name: UpsertImageStorage :one
INSERT INTO imagestorage (uuid, content_checksum, image_size, uploading, cas_path)
VALUES (?, ?, ?, 0, 1)
ON CONFLICT (content_checksum) DO UPDATE SET content_checksum = excluded.content_checksum
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
