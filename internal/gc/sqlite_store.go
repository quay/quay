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

// DeleteBlobRecord revalidates one candidate and deletes it inside a
// transaction. A changed, missing, or newly referenced candidate is skipped.
func (s *SQLiteStore) DeleteBlobRecord(ctx context.Context, candidate OrphanedBlob) (BlobDeletion, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return BlobDeletion{}, err
	}
	defer func() { _ = tx.Rollback() }()

	q := daldb.New(tx)

	var checksum sql.NullString
	var imageSize sql.NullInt64
	if err := tx.QueryRowContext(ctx, "SELECT content_checksum, image_size FROM imagestorage WHERE id = ?", candidate.ID).Scan(&checksum, &imageSize); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return BlobDeletion{}, nil
		}
		return BlobDeletion{}, fmt.Errorf("read blob candidate %d: %w", candidate.ID, err)
	}

	actualChecksum := ""
	if checksum.Valid {
		actualChecksum = checksum.String
	}
	actualSize := int64(0)
	if imageSize.Valid {
		actualSize = imageSize.Int64
	}
	if actualChecksum != candidate.ContentChecksum || actualSize != candidate.ImageSize {
		return BlobDeletion{}, nil
	}

	mbRefs, err := q.CountManifestBlobRefs(ctx, candidate.ID)
	if err != nil {
		return BlobDeletion{}, fmt.Errorf("revalidate manifestblob for blob %d: %w", candidate.ID, err)
	}
	ubRefs, err := q.CountActiveUploadedBlobRefs(ctx, candidate.ID)
	if err != nil {
		return BlobDeletion{}, fmt.Errorf("revalidate uploadedblob for blob %d: %w", candidate.ID, err)
	}
	if mbRefs > 0 || ubRefs > 0 {
		return BlobDeletion{}, nil
	}

	if err := q.DeleteUploadedBlobsByBlobID(ctx, candidate.ID); err != nil {
		return BlobDeletion{}, fmt.Errorf("delete uploadedblobs for blob %d: %w", candidate.ID, err)
	}
	if err := q.DeleteImageStoragePlacements(ctx, candidate.ID); err != nil {
		return BlobDeletion{}, fmt.Errorf("delete placements for blob %d: %w", candidate.ID, err)
	}
	if err := q.DeleteImageStorageSignatures(ctx, candidate.ID); err != nil {
		return BlobDeletion{}, fmt.Errorf("delete signatures for blob %d: %w", candidate.ID, err)
	}
	if err := q.DeleteImageStorage(ctx, candidate.ID); err != nil {
		return BlobDeletion{}, fmt.Errorf("delete imagestorage %d: %w", candidate.ID, err)
	}

	deleteFromStorage := false
	if checksum.Valid {
		count, err := q.CountBlobsByChecksum(ctx, checksum)
		if err != nil {
			return BlobDeletion{}, fmt.Errorf("count blobs for checksum %s: %w", actualChecksum, err)
		}
		deleteFromStorage = count == 0
	}

	if err := tx.Commit(); err != nil {
		return BlobDeletion{}, fmt.Errorf("commit blob delete %d: %w", candidate.ID, err)
	}

	return BlobDeletion{
		Deleted:           true,
		ContentChecksum:   actualChecksum,
		ImageSize:         actualSize,
		DeleteFromStorage: deleteFromStorage,
	}, nil
}
