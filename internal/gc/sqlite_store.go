package gc

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/quay/quay/internal/dal/daldb"
)

// SQLiteStore implements Store using SQLite. All mutations run inside
// transactions and handle FK-dependent row cleanup internally.
type SQLiteStore struct {
	db *sql.DB
}

// NewSQLiteStore creates a Store backed by the given SQLite database.
func NewSQLiteStore(db *sql.DB) *SQLiteStore {
	return &SQLiteStore{db: db}
}

// CleanExpiredUploadedBlobs removes uploadedblob rows past their expiry.
func (s *SQLiteStore) CleanExpiredUploadedBlobs(ctx context.Context) error {
	return daldb.New(s.db).CleanExpiredUploadedBlobs(ctx)
}

// FindExpiredTags returns tags whose soft-delete grace period has elapsed.
func (s *SQLiteStore) FindExpiredTags(ctx context.Context) ([]ExpiredTag, error) {
	rows, err := daldb.New(s.db).FindExpiredTags(ctx)
	if err != nil {
		return nil, err
	}
	tags := make([]ExpiredTag, len(rows))
	for i, r := range rows {
		tags[i] = ExpiredTag{ID: r.ID, Name: r.Name, RepositoryID: r.RepositoryID}
	}
	return tags, nil
}

// DeleteExpiredTags deletes tags and their dependent tagnotificationsuccess
// rows in a single transaction.
func (s *SQLiteStore) DeleteExpiredTags(ctx context.Context, ids []int64) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	q := daldb.New(tx)
	for _, id := range ids {
		if err := q.DeleteTagNotifications(ctx, id); err != nil {
			return fmt.Errorf("delete tag notifications for tag %d: %w", id, err)
		}
		if err := q.DeleteExpiredTag(ctx, id); err != nil {
			return fmt.Errorf("delete tag %d: %w", id, err)
		}
	}
	return tx.Commit()
}

// FindOrphanedManifests returns manifests with no tags, no parent refs, no subject refs.
func (s *SQLiteStore) FindOrphanedManifests(ctx context.Context) ([]OrphanedManifest, error) {
	rows, err := daldb.New(s.db).FindOrphanedManifests(ctx)
	if err != nil {
		return nil, err
	}
	manifests := make([]OrphanedManifest, len(rows))
	for i, r := range rows {
		manifests[i] = OrphanedManifest{ID: r.ID, RepositoryID: r.RepositoryID, Digest: r.Digest}
	}
	return manifests, nil
}

// DeleteManifest removes a manifest and all FK-dependent rows in a single
// transaction. Race-safe because SQLite MaxOpenConns=1 serializes all writes
// through a single connection.
func (s *SQLiteStore) DeleteManifest(ctx context.Context, id int64) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	q := daldb.New(tx)
	if err := q.DeleteManifestLabels(ctx, id); err != nil {
		return err
	}
	if err := q.DeleteManifestChildren(ctx, daldb.DeleteManifestChildrenParams{
		ManifestID:      id,
		ChildManifestID: id,
	}); err != nil {
		return err
	}
	if err := q.DeleteManifestBlobs(ctx, id); err != nil {
		return err
	}
	if err := q.DeleteManifestSecurityStatus(ctx, id); err != nil {
		return err
	}
	if err := q.DeleteTagsByManifest(ctx, sql.NullInt64{Int64: id, Valid: true}); err != nil {
		return err
	}
	if err := q.DeleteManifest(ctx, id); err != nil {
		return err
	}
	return tx.Commit()
}

// FindOrphanedBlobs returns blobs not referenced by any manifest or active uploadedblob.
func (s *SQLiteStore) FindOrphanedBlobs(ctx context.Context) ([]OrphanedBlob, error) {
	rows, err := daldb.New(s.db).FindOrphanedBlobs(ctx)
	if err != nil {
		return nil, err
	}
	blobs := make([]OrphanedBlob, len(rows))
	for i, r := range rows {
		var checksum string
		if r.ContentChecksum.Valid {
			checksum = r.ContentChecksum.String
		}
		var size int64
		if r.ImageSize.Valid {
			size = r.ImageSize.Int64
		}
		blobs[i] = OrphanedBlob{ID: r.ID, ContentChecksum: checksum, ImageSize: size}
	}
	return blobs, nil
}

// DeleteBlobRecords revalidates each candidate, deletes only blobs that are
// still orphaned, and returns checksums safe to delete from storage.
func (s *SQLiteStore) DeleteBlobRecords(ctx context.Context, ids []int64) ([]string, error) {
	var deleted []string
	seen := make(map[string]bool)

	for _, id := range ids {
		checksum, err := s.deleteBlobIfStillOrphaned(ctx, id)
		if err != nil {
			return nil, err
		}
		if checksum == "" {
			continue
		}
		if !seen[checksum] {
			seen[checksum] = true
			count, err := daldb.New(s.db).CountBlobsByChecksum(ctx, sql.NullString{String: checksum, Valid: true})
			if err != nil {
				return nil, fmt.Errorf("count blobs for checksum %s: %w", checksum, err)
			}
			if count == 0 {
				deleted = append(deleted, checksum)
			}
		}
	}
	return deleted, nil
}

// deleteBlobIfStillOrphaned revalidates a single blob inside a transaction.
// Returns the checksum if deleted, empty string if skipped (no longer orphaned).
func (s *SQLiteStore) deleteBlobIfStillOrphaned(ctx context.Context, id int64) (string, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return "", err
	}
	defer func() { _ = tx.Rollback() }()

	q := daldb.New(tx)

	mbRefs, err := q.CountManifestBlobRefs(ctx, id)
	if err != nil {
		return "", fmt.Errorf("revalidate manifestblob for blob %d: %w", id, err)
	}
	ubRefs, err := q.CountActiveUploadedBlobRefs(ctx, id)
	if err != nil {
		return "", fmt.Errorf("revalidate uploadedblob for blob %d: %w", id, err)
	}
	if mbRefs > 0 || ubRefs > 0 {
		return "", nil
	}

	var checksum sql.NullString
	if err := tx.QueryRowContext(ctx, "SELECT content_checksum FROM imagestorage WHERE id = ?", id).Scan(&checksum); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return "", nil
		}
		return "", fmt.Errorf("read checksum for blob %d: %w", id, err)
	}

	if err := q.DeleteUploadedBlobsByBlobID(ctx, id); err != nil {
		return "", fmt.Errorf("delete uploadedblobs for blob %d: %w", id, err)
	}
	if err := q.DeleteImageStoragePlacements(ctx, id); err != nil {
		return "", fmt.Errorf("delete placements for blob %d: %w", id, err)
	}
	if err := q.DeleteImageStorageSignatures(ctx, id); err != nil {
		return "", fmt.Errorf("delete signatures for blob %d: %w", id, err)
	}
	if err := q.DeleteImageStorage(ctx, id); err != nil {
		return "", fmt.Errorf("delete imagestorage %d: %w", id, err)
	}

	if err := tx.Commit(); err != nil {
		return "", fmt.Errorf("commit blob delete %d: %w", id, err)
	}

	if checksum.Valid {
		return checksum.String, nil
	}
	return "", nil
}
