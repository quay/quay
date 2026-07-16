package metastore

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/oci"
)

// SQLiteStore implements Store backed by a SQLite database. It holds only a
// *sql.DB and cached enum IDs. All transactional methods bind daldb.Queries
// to the transaction via WithTx---never to the pool---preventing deadlocks
// under MaxOpenConns=1.
type SQLiteStore struct {
	db *sql.DB

	visibilityPrivate int64
	repoKindImage     int64
	tagKindTag        int64

	mediaTypesMu sync.RWMutex
	mediaTypes   map[string]int64
	nowMs        func() int64
}

// compile-time check
var _ oci.MetadataStore = (*SQLiteStore)(nil)

// DB returns the underlying database handle, primarily for use in tests.
func (s *SQLiteStore) DB() *sql.DB { return s.db }

// SQLiteStoreOption configures a SQLiteStore during construction.
type SQLiteStoreOption func(*SQLiteStore)

// WithNowFunc overrides the store clock. It is primarily useful for deterministic tests.
func WithNowFunc(nowMs func() int64) SQLiteStoreOption {
	return func(s *SQLiteStore) {
		if nowMs != nil {
			s.nowMs = nowMs
		}
	}
}

// NewSQLiteStore creates a Store backed by the given SQLite database. It
// caches frequently-used enum IDs at construction time.
func NewSQLiteStore(ctx context.Context, db *sql.DB, opts ...SQLiteStoreOption) (*SQLiteStore, error) {
	s := &SQLiteStore{
		db:         db,
		mediaTypes: make(map[string]int64),
		nowMs:      func() int64 { return time.Now().UnixMilli() },
	}
	for _, opt := range opts {
		opt(s)
	}
	if err := s.cacheEnums(ctx); err != nil {
		return nil, fmt.Errorf("metastore: cache enums: %w", err)
	}
	return s, nil
}

func (s *SQLiteStore) cacheEnums(ctx context.Context) error {
	q := daldb.New(s.db)

	var err error
	if s.visibilityPrivate, err = q.GetVisibilityByName(ctx, "private"); err != nil {
		return fmt.Errorf("visibility 'private': %w", err)
	}
	if s.repoKindImage, err = q.GetRepositoryKindByName(ctx, "image"); err != nil {
		return fmt.Errorf("repositorykind 'image': %w", err)
	}
	if s.tagKindTag, err = q.GetTagKindByName(ctx, "tag"); err != nil {
		return fmt.Errorf("tagkind 'tag': %w", err)
	}

	mts, err := q.GetAllMediaTypes(ctx)
	if err != nil {
		return fmt.Errorf("mediatype: %w", err)
	}
	for _, mt := range mts {
		s.mediaTypes[mt.Name] = mt.ID
	}
	return nil
}

// resolveMediaType returns the cached ID for a media type string. All valid
// manifest media types are pre-seeded; distribution rejects unknown types
// before they reach the middleware, so a cache miss is a deployment bug.
func (s *SQLiteStore) resolveMediaType(mt string) (int64, error) {
	s.mediaTypesMu.RLock()
	id, ok := s.mediaTypes[mt]
	s.mediaTypesMu.RUnlock()
	if !ok {
		return 0, fmt.Errorf("unknown media type %q: not in seed data", mt)
	}
	return id, nil
}

// EnsureRepository creates or retrieves the repository and its namespace user.
func (s *SQLiteStore) EnsureRepository(ctx context.Context, name oci.RepositoryName) (int64, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	q := daldb.New(tx)

	userID, err := q.EnsureUser(ctx, name.Namespace)
	if err != nil {
		return 0, fmt.Errorf("ensure user %q: %w", name.Namespace, err)
	}

	repoID, err := q.GetOrCreateRepository(ctx, daldb.GetOrCreateRepositoryParams{
		NamespaceUserID: sql.NullInt64{Int64: userID, Valid: true},
		Name:            name.Name,
		VisibilityID:    s.visibilityPrivate,
		KindID:          s.repoKindImage,
		BadgeToken:      "",
	})
	if err != nil {
		return 0, fmt.Errorf("ensure repository %q: %w", name.String(), err)
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit: %w", err)
	}
	return repoID, nil
}

// PutManifest upserts a manifest and its blob/child references within a transaction.
func (s *SQLiteStore) PutManifest(ctx context.Context, repoID int64, m oci.ManifestRecord) (int64, error) { //nolint:gocritic // interface compliance
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	q := daldb.New(tx)

	mtID, err := s.resolveMediaType(m.MediaType)
	if err != nil {
		return 0, err
	}

	manifestID, err := q.UpsertManifest(ctx, daldb.UpsertManifestParams{
		RepositoryID:  repoID,
		Digest:        m.Digest.String(),
		MediaTypeID:   mtID,
		ManifestBytes: string(m.Content),
		Subject:       sql.NullString{String: m.Subject.String(), Valid: m.Subject != ""},
		ArtifactType:  sql.NullString{String: m.ArtifactType, Valid: m.ArtifactType != ""},
	})
	if err != nil {
		return 0, fmt.Errorf("upsert manifest %s: %w", m.Digest, err)
	}

	for _, ref := range m.BlobDigests {
		blobID, err := s.ensureBlob(ctx, tx, ref)
		if err != nil {
			return 0, err
		}
		if err := q.LinkManifestBlob(ctx, daldb.LinkManifestBlobParams{
			RepositoryID: repoID,
			ManifestID:   manifestID,
			BlobID:       blobID,
		}); err != nil {
			return 0, fmt.Errorf("link manifest blob %s: %w", ref.Digest, err)
		}
	}

	for _, childDgst := range m.ChildDigests {
		if err := s.linkChild(ctx, q, repoID, manifestID, mtID, childDgst); err != nil {
			return 0, err
		}
	}

	if m.Tag != "" {
		if _, err := s.putTag(ctx, q, repoID, manifestID, m.Tag); err != nil {
			return 0, err
		}
	}

	if m.Subject != "" {
		if err := s.setSubjectAndProtect(ctx, q, repoID, manifestID, &m); err != nil {
			return 0, err
		}
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit: %w", err)
	}
	return manifestID, nil
}

// setSubjectAndProtect sets the subject column on a manifest and creates a
// hidden tag to protect the referrer from GC. Referrer manifests typically
// have no user-visible tag, so without the hidden tag FindOrphanedManifests
// would collect them.
func (s *SQLiteStore) setSubjectAndProtect(ctx context.Context, q *daldb.Queries, repoID, manifestID int64, m *oci.ManifestRecord) error {
	if err := q.SetManifestSubject(ctx, daldb.SetManifestSubjectParams{
		Subject: sql.NullString{String: m.Subject.String(), Valid: true},
		ID:      manifestID,
	}); err != nil {
		return fmt.Errorf("set manifest subject %s: %w", m.Subject, err)
	}
	if _, err := q.InsertHiddenTag(ctx, daldb.InsertHiddenTagParams{
		Name:            "$referrer-" + m.Digest.Algorithm().String() + "-" + m.Digest.Encoded(),
		RepositoryID:    repoID,
		ManifestID:      sql.NullInt64{Int64: manifestID, Valid: true},
		LifetimeStartMs: s.nowMs(),
		TagKindID:       s.tagKindTag,
	}); err != nil {
		return fmt.Errorf("insert hidden referrer tag: %w", err)
	}
	return nil
}

// linkChild resolves or creates a child manifest and links it to the parent
// via manifestchild. Under concurrent multi-arch pushes, the child's metadata
// write may not have committed yet even though distribution accepted the blob.
// In that case, we create a placeholder manifest row so the FK link succeeds.
func (s *SQLiteStore) linkChild(ctx context.Context, q *daldb.Queries, repoID, manifestID, mtID int64, childDgst digest.Digest) error {
	child, err := q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoID,
		Digest:       childDgst.String(),
	})
	if errors.Is(err, sql.ErrNoRows) {
		child.ID, err = q.UpsertManifest(ctx, daldb.UpsertManifestParams{
			RepositoryID:  repoID,
			Digest:        childDgst.String(),
			MediaTypeID:   mtID,
			ManifestBytes: "{}",
		})
		if err != nil {
			return fmt.Errorf("ensure child manifest %s: %w", childDgst, err)
		}
	} else if err != nil {
		return fmt.Errorf("lookup child manifest %s: %w", childDgst, err)
	}
	if err := q.LinkManifestChild(ctx, daldb.LinkManifestChildParams{
		RepositoryID:    repoID,
		ManifestID:      manifestID,
		ChildManifestID: child.ID,
	}); err != nil {
		return fmt.Errorf("link child manifest %s: %w", childDgst, err)
	}
	return nil
}

// ensureBlob inserts a blob into imagestorage if it doesn't already exist,
// returning its ID. Uses SELECT-first because content_checksum has a
// non-unique index (the sqlc UpsertImageStorage ON CONFLICT clause targets
// content_checksum which won't work). The db parameter must be the same
// handle (pool or tx) used by the caller to avoid deadlocks.
func (s *SQLiteStore) ensureBlob(ctx context.Context, db daldb.DBTX, ref oci.BlobRef) (int64, error) {
	q := daldb.New(db)
	checksum := sql.NullString{String: ref.Digest.String(), Valid: true}

	id, err := q.GetBlobByChecksum(ctx, checksum)
	if err == nil {
		return id, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return 0, fmt.Errorf("lookup blob %s: %w", ref.Digest, err)
	}

	id, err = q.InsertBlob(ctx, daldb.InsertBlobParams{
		Uuid:            ref.Digest.Encoded(),
		ContentChecksum: checksum,
		ImageSize:       sql.NullInt64{Int64: ref.Size, Valid: ref.Size > 0},
	})
	if err != nil {
		return 0, fmt.Errorf("insert blob %s: %w", ref.Digest, err)
	}
	return id, nil
}

// DeleteManifest removes a manifest and all its FK references within a transaction.
func (s *SQLiteStore) DeleteManifest(ctx context.Context, repoID int64, dgst digest.Digest) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	q := daldb.New(tx)

	manifest, err := q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoID,
		Digest:       dgst.String(),
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("lookup manifest %s: %w", dgst, err)
	}

	// Order follows Python's gc.py: clear all FK references, then delete
	// the manifest row itself. Tags must be fully deleted (not just expired)
	// because even expired tags hold an FK to the manifest.
	mid := sql.NullInt64{Int64: manifest.ID, Valid: true}
	if err := q.DeleteTagsByManifest(ctx, mid); err != nil {
		return fmt.Errorf("delete manifest tags: %w", err)
	}
	if err := q.DeleteManifestLabels(ctx, manifest.ID); err != nil {
		return fmt.Errorf("delete manifest labels: %w", err)
	}
	if err := q.DeleteManifestChildren(ctx, daldb.DeleteManifestChildrenParams{
		ManifestID:      manifest.ID,
		ChildManifestID: manifest.ID,
	}); err != nil {
		return fmt.Errorf("delete manifest child links: %w", err)
	}
	if err := q.DeleteManifestBlobs(ctx, manifest.ID); err != nil {
		return fmt.Errorf("delete manifest blob links: %w", err)
	}
	if err := q.DeleteManifestSecurityStatus(ctx, manifest.ID); err != nil {
		return fmt.Errorf("delete manifest security status: %w", err)
	}
	if err := q.DeleteManifest(ctx, manifest.ID); err != nil {
		return fmt.Errorf("delete manifest: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit: %w", err)
	}
	return nil
}

// PutBlob inserts or retrieves a blob by its content checksum.
func (s *SQLiteStore) PutBlob(ctx context.Context, b oci.BlobRecord) (int64, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op

	id, err := s.ensureBlob(ctx, tx, oci.BlobRef(b))
	if err != nil {
		return 0, err
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit: %w", err)
	}
	return id, nil
}

// PutRepositoryBlob atomically inserts the blob metadata and its upload
// protection marker in a single transaction, closing the race window where
// GC could see the imagestorage row before the uploadedblob row exists.
func (s *SQLiteStore) PutRepositoryBlob(ctx context.Context, repoID int64, b oci.BlobRecord) (int64, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op

	blobID, err := s.ensureBlob(ctx, tx, oci.BlobRef(b))
	if err != nil {
		return 0, err
	}

	if err := daldb.New(tx).InsertUploadedBlob(ctx, daldb.InsertUploadedBlobParams{
		RepositoryID: repoID,
		BlobID:       blobID,
	}); err != nil {
		return 0, fmt.Errorf("insert uploaded blob %s: %w", b.Digest, err)
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit: %w", err)
	}
	return blobID, nil
}

// PutTag expires any active tag with the same name and inserts a new one.
func (s *SQLiteStore) PutTag(ctx context.Context, repoID int64, t oci.TagRecord) (int64, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	q := daldb.New(tx)

	manifest, err := q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoID,
		Digest:       t.Digest.String(),
	})
	if err != nil {
		return 0, fmt.Errorf("lookup manifest for tag %q: %w", t.Name, err)
	}

	id, err := s.putTag(ctx, q, repoID, manifest.ID, t.Name)
	if err != nil {
		return 0, err
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit: %w", err)
	}
	return id, nil
}

// putTag expires any active tag with the same name, then inserts a new one.
// Re-pushing the same manifest digest is idempotent and preserves tag history.
func (s *SQLiteStore) putTag(ctx context.Context, q *daldb.Queries, repoID, manifestID int64, tag string) (int64, error) {
	now := s.nowMs()

	activeTag, err := q.GetActiveTag(ctx, daldb.GetActiveTagParams{
		RepositoryID: repoID,
		Name:         tag,
	})
	if errors.Is(err, sql.ErrNoRows) {
		latestTag, latestErr := q.GetLatestTagInterval(ctx, daldb.GetLatestTagIntervalParams{
			RepositoryID: repoID,
			Name:         tag,
		})
		if errors.Is(latestErr, sql.ErrNoRows) {
			return s.insertTag(ctx, q, repoID, manifestID, tag, now)
		}
		if latestErr != nil {
			return 0, fmt.Errorf("lookup latest tag interval %q: %w", tag, latestErr)
		}
		if now < latestTag.LifetimeStartMs {
			now = latestTag.LifetimeStartMs
		}
		if latestTag.LifetimeEndMs.Valid && now < latestTag.LifetimeEndMs.Int64 {
			now = latestTag.LifetimeEndMs.Int64
		}
		return s.insertTag(ctx, q, repoID, manifestID, tag, now)
	}
	if err != nil {
		return 0, fmt.Errorf("lookup active tag %q: %w", tag, err)
	}
	if activeTag.ManifestID.Valid && activeTag.ManifestID.Int64 == manifestID {
		return activeTag.ID, nil
	}
	if now < activeTag.LifetimeStartMs {
		now = activeTag.LifetimeStartMs
	}

	if err := s.expireActiveTag(ctx, q, activeTag.ID, now); err != nil {
		return 0, fmt.Errorf("expire tag %q: %w", tag, err)
	}
	return s.insertTag(ctx, q, repoID, manifestID, tag, now)
}

func (s *SQLiteStore) insertTag(ctx context.Context, q *daldb.Queries, repoID, manifestID int64, tag string, now int64) (int64, error) {
	id, err := q.InsertTag(ctx, daldb.InsertTagParams{
		Name:            tag,
		RepositoryID:    repoID,
		ManifestID:      sql.NullInt64{Int64: manifestID, Valid: true},
		LifetimeStartMs: now,
		TagKindID:       s.tagKindTag,
	})
	if err != nil {
		return 0, fmt.Errorf("insert tag %q: %w", tag, err)
	}
	return id, nil
}

func (s *SQLiteStore) expireActiveTag(ctx context.Context, q *daldb.Queries, tagID, now int64) error {
	result, err := q.ExpireTagByID(ctx, daldb.ExpireTagByIDParams{
		LifetimeEndMs: sql.NullInt64{Int64: now, Valid: true},
		ID:            tagID,
	})
	if err != nil {
		return fmt.Errorf("expire active tag row %d: %w", tagID, err)
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("expire active tag row %d rows affected: %w", tagID, err)
	}
	if rows != 1 {
		return fmt.Errorf("expire active tag row %d: updated %d rows", tagID, rows)
	}
	return nil
}

// DeleteTag expires the active tag by setting lifetime_end_ms.
func (s *SQLiteStore) DeleteTag(ctx context.Context, repoID int64, tag string) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	q := daldb.New(tx)

	activeTag, err := q.GetActiveTag(ctx, daldb.GetActiveTagParams{
		RepositoryID: repoID,
		Name:         tag,
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("lookup active tag %q: %w", tag, err)
	}

	now := s.nowMs()
	if now < activeTag.LifetimeStartMs {
		now = activeTag.LifetimeStartMs
	}
	if err := s.expireActiveTag(ctx, q, activeTag.ID, now); err != nil {
		return fmt.Errorf("expire tag %q: %w", tag, err)
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit: %w", err)
	}
	return nil
}

// GetRepositoryID retrieves the repository ID by namespace and name.
func (s *SQLiteStore) GetRepositoryID(ctx context.Context, name oci.RepositoryName) (int64, error) {
	q := daldb.New(s.db)
	id, err := q.GetRepositoryByNamespaceName(ctx, daldb.GetRepositoryByNamespaceNameParams{
		Username: name.Namespace,
		Name:     name.Name,
	})
	if errors.Is(err, sql.ErrNoRows) {
		return 0, fmt.Errorf("get repository %s: %w", name, oci.ErrNotExist)
	}
	if err != nil {
		return 0, fmt.Errorf("get repository %s: %w", name, err)
	}
	return id, nil
}

// GetTagDigest retrieves the manifest digest for a live tag.
func (s *SQLiteStore) GetTagDigest(ctx context.Context, repoID int64, tag string) (digest.Digest, error) {
	q := daldb.New(s.db)
	now := s.nowMs()
	d, err := q.GetLiveTagDigest(ctx, daldb.GetLiveTagDigestParams{
		RepositoryID:    repoID,
		Name:            tag,
		LifetimeStartMs: now,
		LifetimeEndMs:   sql.NullInt64{Int64: now, Valid: true},
	})
	if errors.Is(err, sql.ErrNoRows) {
		return "", fmt.Errorf("get tag %q: %w", tag, oci.ErrNotExist)
	}
	if err != nil {
		return "", fmt.Errorf("get tag %q: %w", tag, err)
	}
	return digest.Parse(d)
}

// GetManifestDigest verifies a manifest exists in the repository and returns its digest.
func (s *SQLiteStore) GetManifestDigest(ctx context.Context, repoID int64, dgst digest.Digest) (digest.Digest, error) {
	q := daldb.New(s.db)
	d, err := q.ManifestExistsByDigest(ctx, daldb.ManifestExistsByDigestParams{
		RepositoryID: repoID,
		Digest:       dgst.String(),
	})
	if errors.Is(err, sql.ErrNoRows) {
		return "", fmt.Errorf("get manifest %s: %w", dgst, oci.ErrNotExist)
	}
	if err != nil {
		return "", fmt.Errorf("get manifest %s: %w", dgst, err)
	}
	return digest.Parse(d)
}

// GetManifestContent returns manifest JSON stored in the database.
func (s *SQLiteStore) GetManifestContent(ctx context.Context, dgst digest.Digest) ([]byte, error) {
	q := daldb.New(s.db)
	content, err := q.GetManifestContentByDigest(ctx, dgst.String())
	if errors.Is(err, sql.ErrNoRows) {
		return nil, fmt.Errorf("get manifest content %s: %w", dgst, oci.ErrNotExist)
	}
	if err != nil {
		return nil, fmt.Errorf("get manifest content %s: %w", dgst, err)
	}
	return []byte(content), nil
}

// BlobLinkedToRepo checks if a blob is linked to a specific repository via
// manifestblob or uploadedblob (matching Python's get_repository_blob_by_digest).
func (s *SQLiteStore) BlobLinkedToRepo(ctx context.Context, repoID int64, dgst digest.Digest) (bool, error) {
	q := daldb.New(s.db)
	checksum := sql.NullString{String: dgst.String(), Valid: true}
	_, err := q.BlobLinkedToRepo(ctx, daldb.BlobLinkedToRepoParams{
		ContentChecksum: checksum,
		RepositoryID:    repoID,
		RepositoryID_2:  repoID,
	})
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("blob linked to repo %d %s: %w", repoID, dgst, err)
	}
	return true, nil
}

// BlobExists checks if a blob exists in the global storage.
func (s *SQLiteStore) BlobExists(ctx context.Context, dgst digest.Digest) (bool, error) {
	q := daldb.New(s.db)
	checksum := sql.NullString{String: dgst.String(), Valid: true}
	_, err := q.GetBlobByChecksum(ctx, checksum)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("blob exists %s: %w", dgst, err)
	}
	return true, nil
}

// ListTags returns all visible tags for a repository.
func (s *SQLiteStore) ListTags(ctx context.Context, repoID int64) ([]string, error) {
	q := daldb.New(s.db)
	now := s.nowMs()
	tags, err := q.GetTagsByRepository(ctx, daldb.GetTagsByRepositoryParams{
		RepositoryID:    repoID,
		LifetimeStartMs: now,
		LifetimeEndMs:   sql.NullInt64{Int64: now, Valid: true},
	})
	if err != nil {
		return nil, fmt.Errorf("list tags: %w", err)
	}
	return tags, nil
}

// ListRepositories returns all repositories.
func (s *SQLiteStore) ListRepositories(ctx context.Context) ([]oci.RepositoryName, error) {
	q := daldb.New(s.db)
	rows, err := q.ListAllRepositories(ctx)
	if err != nil {
		return nil, fmt.Errorf("list repositories: %w", err)
	}
	repos := make([]oci.RepositoryName, len(rows))
	for i, r := range rows {
		repos[i] = oci.RepositoryName{Namespace: r.Namespace, Name: r.Name}
	}
	return repos, nil
}

// ListReferrers returns manifests that reference the given subject digest.
func (s *SQLiteStore) ListReferrers(ctx context.Context, repoID int64, subject digest.Digest, artifactType string) ([]oci.ReferrerRecord, error) {
	q := daldb.New(s.db)
	subjectStr := sql.NullString{String: subject.String(), Valid: true}

	type row struct {
		Digest        string
		MediaType     string
		ArtifactType  sql.NullString
		Size          sql.NullInt64
		ManifestBytes string
	}
	var rows []row

	if artifactType != "" {
		res, err := q.ListReferrersByArtifactType(ctx, daldb.ListReferrersByArtifactTypeParams{
			RepositoryID: repoID,
			Subject:      subjectStr,
			ArtifactType: sql.NullString{String: artifactType, Valid: true},
		})
		if err != nil {
			return nil, fmt.Errorf("list referrers by artifact type: %w", err)
		}
		for _, r := range res {
			rows = append(rows, row{r.Digest, r.MediaType, r.ArtifactType, r.Size, r.ManifestBytes})
		}
	} else {
		res, err := q.ListReferrers(ctx, daldb.ListReferrersParams{
			RepositoryID: repoID,
			Subject:      subjectStr,
		})
		if err != nil {
			return nil, fmt.Errorf("list referrers: %w", err)
		}
		for _, r := range res {
			rows = append(rows, row{r.Digest, r.MediaType, r.ArtifactType, r.Size, r.ManifestBytes})
		}
	}

	seen := make(map[string]bool, len(rows))
	out := make([]oci.ReferrerRecord, 0, len(rows))
	for _, r := range rows {
		seen[r.Digest] = true
		out = append(out, oci.ReferrerRecord{
			Digest:       r.Digest,
			MediaType:    r.MediaType,
			ArtifactType: r.ArtifactType.String,
			Size:         r.Size.Int64,
			Annotations:  parseAnnotations(r.ManifestBytes),
		})
	}

	fallback, err := s.fallbackTagReferrers(ctx, q, repoID, subject, artifactType, seen)
	if err != nil {
		return nil, fmt.Errorf("fallback tag referrers: %w", err)
	}
	out = append(out, fallback...)
	return out, nil
}

// fallbackTagReferrers looks up the OCI referrers fallback tag schema
// (tag named "sha256-<encoded>") and extracts descriptors from the index.
// Returns (nil, nil) when the fallback tag does not exist.
func (s *SQLiteStore) fallbackTagReferrers(ctx context.Context, q *daldb.Queries, repoID int64, subject digest.Digest, artifactType string, seen map[string]bool) ([]oci.ReferrerRecord, error) {
	tagName := strings.Replace(subject.String(), ":", "-", 1)
	now := s.nowMs()
	tagDigest, err := q.GetLiveTagDigest(ctx, daldb.GetLiveTagDigestParams{
		RepositoryID:    repoID,
		Name:            tagName,
		LifetimeStartMs: now,
		LifetimeEndMs:   sql.NullInt64{Int64: now, Valid: true},
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("get fallback tag %q: %w", tagName, err)
	}
	content, err := q.GetManifestContentByDigest(ctx, tagDigest)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("get fallback manifest %s: %w", tagDigest, err)
	}

	var idx struct {
		Manifests []struct {
			MediaType    string            `json:"mediaType"`
			Digest       string            `json:"digest"`
			Size         int64             `json:"size"`
			ArtifactType string            `json:"artifactType"`
			Annotations  map[string]string `json:"annotations"`
		} `json:"manifests"`
	}
	if err := json.Unmarshal([]byte(content), &idx); err != nil {
		return nil, nil //nolint:nilerr // malformed fallback index is treated as absent
	}

	var out []oci.ReferrerRecord
	for _, m := range idx.Manifests {
		if seen[m.Digest] {
			continue
		}
		if artifactType != "" && m.ArtifactType != artifactType {
			continue
		}
		out = append(out, oci.ReferrerRecord{
			Digest:       m.Digest,
			MediaType:    m.MediaType,
			ArtifactType: m.ArtifactType,
			Size:         m.Size,
			Annotations:  m.Annotations,
		})
	}
	return out, nil
}

func parseAnnotations(manifestBytes string) map[string]string {
	var parsed struct {
		Annotations map[string]string `json:"annotations"`
	}
	if json.Unmarshal([]byte(manifestBytes), &parsed) == nil && len(parsed.Annotations) > 0 {
		return parsed.Annotations
	}
	return nil
}

// PutUploadedBlob marks a blob as recently uploaded to protect it from GC.
func (s *SQLiteStore) PutUploadedBlob(ctx context.Context, repoID int64, dgst digest.Digest) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	q := daldb.New(tx)

	checksum := sql.NullString{String: dgst.String(), Valid: true}
	blobID, err := q.GetBlobByChecksum(ctx, checksum)
	if err != nil {
		return fmt.Errorf("lookup blob %s: %w", dgst, err)
	}

	if err := q.InsertUploadedBlob(ctx, daldb.InsertUploadedBlobParams{
		RepositoryID: repoID,
		BlobID:       blobID,
	}); err != nil {
		return fmt.Errorf("insert uploaded blob %s: %w", dgst, err)
	}

	return tx.Commit()
}

// DeleteUploadedBlob removes a repository-scoped upload marker for a blob.
func (s *SQLiteStore) DeleteUploadedBlob(ctx context.Context, repoID int64, dgst digest.Digest) (int64, error) {
	q := daldb.New(s.db)
	checksum := sql.NullString{String: dgst.String(), Valid: true}

	rows, err := q.DeleteUploadedBlob(ctx, daldb.DeleteUploadedBlobParams{
		RepositoryID:    repoID,
		ContentChecksum: checksum,
	})
	if err != nil {
		return 0, fmt.Errorf("delete uploaded blob %s from repo %d: %w", dgst, repoID, err)
	}
	return rows, nil
}

// CleanExpiredUploadedBlobs removes uploaded blob markers that have expired.
func (s *SQLiteStore) CleanExpiredUploadedBlobs(ctx context.Context) error {
	q := daldb.New(s.db)
	return q.CleanExpiredUploadedBlobs(ctx)
}
