package gc

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strconv"

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

// FindMarkedRepositories returns repositories in the deleted state.
func (s *SQLiteStore) FindMarkedRepositories(ctx context.Context) ([]MarkedRepository, error) {
	rows, err := daldb.New(s.db).FindMarkedRepositories(ctx)
	if err != nil {
		return nil, err
	}
	repos := make([]MarkedRepository, 0, len(rows))
	for _, r := range rows {
		repo := MarkedRepository{ID: r.ID}
		if r.MarkerID.Valid {
			repo.MarkerID = r.MarkerID.Int64
		}
		if r.QueueID.Valid {
			if id, err := strconv.ParseInt(r.QueueID.String, 10, 64); err == nil {
				repo.QueueID = id
			}
		}
		repos = append(repos, repo)
	}
	return repos, nil
}

// PurgeRepository removes all rows owned by a marked repository. The order
// follows Python's purge_repository: tag and manifest dependants first, then
// the manifests, then every table with a repository foreign key, then the
// deletion marker, its queue item, and the repository itself. The repository
// row is only removed while still in state 3 so an active repository can
// never be dropped by mistake.
func (s *SQLiteStore) PurgeRepository(ctx context.Context, repo MarkedRepository) (RepositoryPurge, error) {
	var purge RepositoryPurge

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return purge, err
	}
	defer func() { _ = tx.Rollback() }()
	q := daldb.New(tx)

	tags, err := q.CountTagsByRepository(ctx, repo.ID)
	if err != nil {
		return purge, fmt.Errorf("count tags: %w", err)
	}
	manifests, err := q.CountManifestsByRepository(ctx, repo.ID)
	if err != nil {
		return purge, fmt.Errorf("count manifests: %w", err)
	}

	steps := []struct {
		name string
		fn   func(context.Context, int64) error
	}{
		{"tag notifications", q.DeleteTagNotificationsByRepository},
		{"tags", q.DeleteTagsByRepository},
		{"manifest labels", q.DeleteManifestLabelsByRepository},
		{"manifest children", q.DeleteManifestChildrenByRepository},
		{"manifest blobs", q.DeleteManifestBlobsByRepository},
		{"manifest security status", q.DeleteManifestSecurityStatusByRepository},
		{"manifest pull statistics", q.DeleteManifestPullStatisticsByRepository},
		{"tag pull statistics", q.DeleteTagPullStatisticsByRepository},
		{"manifests", q.DeleteManifestsByRepository},
		{"uploaded blobs", q.DeleteUploadedBlobsByRepository},
		{"blob uploads", q.DeleteBlobUploadsByRepository},
		{"builds", q.DeleteRepositoryBuildsByRepository},
		{"build triggers", q.DeleteRepositoryBuildTriggersByRepository},
		{"access tokens", q.DeleteAccessTokensByRepository},
		{"mirror config", q.DeleteRepoMirrorConfigByRepository},
		{"mirror rules", q.DeleteRepoMirrorRulesByRepository},
		{"org mirror repositories", func(ctx context.Context, id int64) error {
			return q.DeleteOrgMirrorRepositoriesByRepository(ctx, sql.NullInt64{Int64: id, Valid: true})
		}},
		{"appr tags", q.DeleteApprTagsByRepository},
		{"permissions", q.DeleteRepositoryPermissionsByRepository},
		{"notifications", q.DeleteRepositoryNotificationsByRepository},
		{"action counts", q.DeleteRepositoryActionCountsByRepository},
		{"authorized emails", q.DeleteRepositoryAuthorizedEmailsByRepository},
		{"auto-prune policies", q.DeleteRepositoryAutoPrunePoliciesByRepository},
		{"immutability policies", q.DeleteRepositoryImmutabilityPoliciesByRepository},
		{"search scores", q.DeleteRepositorySearchScoresByRepository},
		{"quota sizes", q.DeleteQuotaRepositorySizesByRepository},
		{"stars", q.DeleteStarsByRepositoryForPurge},
		{"deletion markers", q.DeleteDeletedRepositoryMarkers},
	}
	for _, step := range steps {
		if err := step.fn(ctx, repo.ID); err != nil {
			return purge, fmt.Errorf("delete %s for repository %d: %w", step.name, repo.ID, err)
		}
	}
	if repo.QueueID != 0 {
		if err := q.DeleteQueueItem(ctx, repo.QueueID); err != nil {
			return purge, fmt.Errorf("delete queue item %d for repository %d: %w", repo.QueueID, repo.ID, err)
		}
	}
	if err := q.DeleteRepository(ctx, repo.ID); err != nil {
		return purge, fmt.Errorf("delete repository %d: %w", repo.ID, err)
	}
	if err := tx.Commit(); err != nil {
		return purge, err
	}
	purge.TagsDeleted = int(tags)
	purge.ManifestsDeleted = int(manifests)
	return purge, nil
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
	result, checksum, matches, err := readBlobCandidate(ctx, tx, candidate)
	if err != nil {
		return BlobDeletion{}, err
	}
	if !matches {
		return BlobDeletion{}, nil
	}

	protected, err := blobIsProtected(ctx, q, candidate.ID)
	if err != nil {
		return BlobDeletion{}, err
	}
	if protected {
		return BlobDeletion{}, nil
	}

	if err := deleteBlobRows(ctx, q, candidate.ID); err != nil {
		return BlobDeletion{}, err
	}

	if checksum.Valid {
		count, err := q.CountBlobsByChecksum(ctx, checksum)
		if err != nil {
			return BlobDeletion{}, fmt.Errorf("count blobs for checksum %s: %w", result.ContentChecksum, err)
		}
		result.DeleteFromStorage = count == 0
	}

	if err := tx.Commit(); err != nil {
		return BlobDeletion{}, fmt.Errorf("commit blob delete %d: %w", candidate.ID, err)
	}

	result.Deleted = true
	return result, nil
}

func readBlobCandidate(ctx context.Context, tx *sql.Tx, candidate OrphanedBlob) (BlobDeletion, sql.NullString, bool, error) {
	var checksum sql.NullString
	var imageSize sql.NullInt64
	if err := tx.QueryRowContext(ctx, "SELECT content_checksum, image_size FROM imagestorage WHERE id = ?", candidate.ID).Scan(&checksum, &imageSize); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return BlobDeletion{}, sql.NullString{}, false, nil
		}
		return BlobDeletion{}, sql.NullString{}, false, fmt.Errorf("read blob candidate %d: %w", candidate.ID, err)
	}

	result := BlobDeletion{}
	if checksum.Valid {
		result.ContentChecksum = checksum.String
	}
	if imageSize.Valid {
		result.ImageSize = imageSize.Int64
	}
	matches := result.ContentChecksum == candidate.ContentChecksum && result.ImageSize == candidate.ImageSize
	return result, checksum, matches, nil
}

func blobIsProtected(ctx context.Context, q *daldb.Queries, id int64) (bool, error) {
	mbRefs, err := q.CountManifestBlobRefs(ctx, id)
	if err != nil {
		return false, fmt.Errorf("revalidate manifestblob for blob %d: %w", id, err)
	}
	ubRefs, err := q.CountActiveUploadedBlobRefs(ctx, id)
	if err != nil {
		return false, fmt.Errorf("revalidate uploadedblob for blob %d: %w", id, err)
	}
	return mbRefs > 0 || ubRefs > 0, nil
}

func deleteBlobRows(ctx context.Context, q *daldb.Queries, id int64) error {
	if err := q.DeleteUploadedBlobsByBlobID(ctx, id); err != nil {
		return fmt.Errorf("delete uploadedblobs for blob %d: %w", id, err)
	}
	if err := q.DeleteImageStoragePlacements(ctx, id); err != nil {
		return fmt.Errorf("delete placements for blob %d: %w", id, err)
	}
	if err := q.DeleteImageStorageSignatures(ctx, id); err != nil {
		return fmt.Errorf("delete signatures for blob %d: %w", id, err)
	}
	if err := q.DeleteImageStorage(ctx, id); err != nil {
		return fmt.Errorf("delete imagestorage %d: %w", id, err)
	}
	return nil
}
