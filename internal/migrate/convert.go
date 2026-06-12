package migrate

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/quay/quay/internal/dal/dbcore"
)

// convertStorage transforms the copied Python Quay storage layout into the
// distribution/distribution filesystem format that the Go binary's registry expects.
func (m *Migrator) convertStorage(ctx context.Context) error {
	storageRoot := filepath.Join(m.DataDir, "storage")
	distRoot := filepath.Join(storageRoot, "docker", "registry", "v2")

	dbPath := filepath.Join(m.DataDir, "quay.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		return fmt.Errorf("open database: %w", err)
	}
	defer func() { _ = db.Close() }()

	// Step 1: Hard-link existing blobs into distribution layout.
	blobCount, err := convertBlobs(storageRoot, distRoot)
	if err != nil {
		return fmt.Errorf("convert blobs: %w", err)
	}
	slog.Info("converted blobs", "count", blobCount)

	// Step 2: Write manifest bytes as blobs (stored in DB, not on disk in old format).
	manifestCount, err := writeManifestBlobs(ctx, db, distRoot)
	if err != nil {
		return fmt.Errorf("write manifest blobs: %w", err)
	}
	slog.Info("wrote manifest blobs", "count", manifestCount)

	// Step 3: Create repository metadata (link files).
	if err := createRepoMetadata(ctx, db, distRoot); err != nil {
		return fmt.Errorf("create repo metadata: %w", err)
	}

	// Step 4: Remove old storage layout.
	for _, dir := range []string{"sha256", "uploads"} {
		_ = os.RemoveAll(filepath.Join(storageRoot, dir))
	}

	slog.Info("storage converted to distribution format")
	return nil
}

// convertBlobs walks the old sha256/<prefix>/<digest> tree and hard-links each
// blob to docker/registry/v2/blobs/sha256/<prefix>/<digest>/data.
func convertBlobs(storageRoot, distRoot string) (int, error) {
	oldBlobDir := filepath.Join(storageRoot, "sha256")
	if _, err := os.Stat(oldBlobDir); os.IsNotExist(err) {
		return 0, nil
	}

	count := 0
	err := filepath.Walk(oldBlobDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return err
		}

		digest := info.Name()
		rel, _ := filepath.Rel(oldBlobDir, filepath.Dir(path))
		prefix := rel // e.g., "ab"

		dstDir := filepath.Join(distRoot, "blobs", "sha256", prefix, digest)
		dstPath := filepath.Join(dstDir, "data")

		if _, err := os.Stat(dstPath); err == nil {
			return nil // already converted
		}

		if err := os.MkdirAll(dstDir, 0o750); err != nil {
			return fmt.Errorf("mkdir %s: %w", dstDir, err)
		}

		if err := os.Link(path, dstPath); err != nil { //nolint:gosec // migration converts known storage tree
			// Fall back to copy if hard link fails (cross-filesystem).
			if err := copyFileIdempotent(path, dstPath); err != nil {
				return fmt.Errorf("link/copy blob %s: %w", digest, err)
			}
		}

		count++
		return nil
	})

	return count, err
}

// writeManifestBlobs writes each manifest's JSON bytes as a blob in the
// distribution store. Python Quay stores manifests in the DB only.
func writeManifestBlobs(ctx context.Context, db *sql.DB, distRoot string) (int, error) {
	rows, err := db.QueryContext(ctx, "SELECT digest, manifest_bytes FROM manifest")
	if err != nil {
		return 0, fmt.Errorf("query manifests: %w", err)
	}
	defer func() { _ = rows.Close() }()

	count := 0
	for rows.Next() {
		var digest, manifestBytes string
		if err := rows.Scan(&digest, &manifestBytes); err != nil {
			return count, fmt.Errorf("scan manifest: %w", err)
		}

		blobPath, err := distBlobPath(distRoot, digest)
		if err != nil {
			return count, fmt.Errorf("blob path for manifest %s: %w", digest, err)
		}

		if _, err := os.Stat(blobPath); err == nil {
			count++
			continue // already exists
		}

		if err := os.MkdirAll(filepath.Dir(blobPath), 0o750); err != nil {
			return count, err
		}
		if err := os.WriteFile(blobPath, []byte(manifestBytes), 0o644); err != nil { //nolint:gosec // blob data must be world-readable
			return count, fmt.Errorf("write manifest blob %s: %w", digest, err)
		}
		count++
	}

	return count, rows.Err()
}

// createRepoMetadata builds the distribution repositories/ tree with link files.
func createRepoMetadata(ctx context.Context, db *sql.DB, distRoot string) error {
	repoRows, err := db.QueryContext(ctx,
		`SELECT r.id, u.username, r.name FROM repository r
		 JOIN "user" u ON r.namespace_user_id = u.id
		 WHERE r.state = 0`) // NORMAL state
	if err != nil {
		return fmt.Errorf("query repositories: %w", err)
	}
	defer func() { _ = repoRows.Close() }()

	type repo struct {
		id        int64
		namespace string
		name      string
	}
	var repos []repo
	for repoRows.Next() {
		var r repo
		if err := repoRows.Scan(&r.id, &r.namespace, &r.name); err != nil {
			return fmt.Errorf("scan repo: %w", err)
		}
		repos = append(repos, r)
	}
	if err := repoRows.Err(); err != nil {
		return err
	}

	for _, r := range repos {
		repoPath := filepath.Join(distRoot, "repositories", r.namespace, r.name)
		if err := createRepoLinks(ctx, db, repoPath, r.id); err != nil {
			return fmt.Errorf("repo %s/%s: %w", r.namespace, r.name, err)
		}
		slog.Info("created repo metadata", "repo", r.namespace+"/"+r.name)
	}

	return nil
}

func createRepoLinks(ctx context.Context, db *sql.DB, repoPath string, repoID int64) error {
	if err := createRevisionLinks(ctx, db, repoPath, repoID); err != nil {
		return err
	}
	if err := createTagLinks(ctx, db, repoPath, repoID); err != nil {
		return err
	}
	return createLayerLinks(ctx, db, repoPath, repoID)
}

func createRevisionLinks(ctx context.Context, db *sql.DB, repoPath string, repoID int64) error {
	rows, err := db.QueryContext(ctx,
		"SELECT digest FROM manifest WHERE repository_id = ?", repoID)
	if err != nil {
		return fmt.Errorf("query manifest revisions: %w", err)
	}
	defer func() { _ = rows.Close() }()

	for rows.Next() {
		var digest string
		if err := rows.Scan(&digest); err != nil {
			return err
		}
		hex := strings.TrimPrefix(digest, "sha256:")
		if err := writeLink(filepath.Join(repoPath, "_manifests", "revisions", "sha256", hex, "link"), digest); err != nil {
			return err
		}
	}
	return rows.Err()
}

func createTagLinks(ctx context.Context, db *sql.DB, repoPath string, repoID int64) error {
	rows, err := db.QueryContext(ctx,
		`SELECT t.name, m.digest FROM tag t
		 JOIN manifest m ON t.manifest_id = m.id
		 WHERE t.repository_id = ? AND t.lifetime_end_ms IS NULL AND t.hidden = 0`, repoID)
	if err != nil {
		return fmt.Errorf("query tags: %w", err)
	}
	defer func() { _ = rows.Close() }()

	for rows.Next() {
		var tagName, digest string
		if err := rows.Scan(&tagName, &digest); err != nil {
			return err
		}
		hex := strings.TrimPrefix(digest, "sha256:")
		tagDir := filepath.Join(repoPath, "_manifests", "tags", tagName)
		if err := writeLink(filepath.Join(tagDir, "current", "link"), digest); err != nil {
			return err
		}
		if err := writeLink(filepath.Join(tagDir, "index", "sha256", hex, "link"), digest); err != nil {
			return err
		}
	}
	return rows.Err()
}

func createLayerLinks(ctx context.Context, db *sql.DB, repoPath string, repoID int64) error {
	rows, err := db.QueryContext(ctx,
		`SELECT DISTINCT s.content_checksum FROM manifestblob mb
		 JOIN imagestorage s ON mb.blob_id = s.id
		 WHERE mb.repository_id = ?`, repoID)
	if err != nil {
		return fmt.Errorf("query layers: %w", err)
	}
	defer func() { _ = rows.Close() }()

	for rows.Next() {
		var checksum string
		if err := rows.Scan(&checksum); err != nil {
			return err
		}
		hex := strings.TrimPrefix(checksum, "sha256:")
		if err := writeLink(filepath.Join(repoPath, "_layers", "sha256", hex, "link"), checksum); err != nil {
			return err
		}
	}
	return rows.Err()
}

// writeLink creates a distribution link file containing a digest string.
func writeLink(path, digest string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
		return err
	}
	return os.WriteFile(path, []byte(digest), 0o644) //nolint:gosec // migration output file
}

// distBlobPath returns the distribution filesystem path for a blob by digest.
func distBlobPath(distRoot, digest string) (string, error) {
	parts := strings.SplitN(digest, ":", 2)
	if len(parts) != 2 {
		return "", fmt.Errorf("invalid digest format: %s", digest)
	}
	algo, hex := parts[0], parts[1]
	if len(hex) < 2 {
		return "", fmt.Errorf("digest too short: %s", digest)
	}
	return filepath.Join(distRoot, "blobs", algo, hex[:2], hex, "data"), nil
}
