package migrate

import (
	"bytes"
	"database/sql"
	"os"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/dal/dbcore"
)

func TestConvertStorage(t *testing.T) {
	// Set up a minimal data-dir with old Quay storage layout + DB.
	dataDir := t.TempDir()

	// Create old-format blob storage.
	oldBlobDir := filepath.Join(dataDir, "storage", "sha256", "ab")
	if err := os.MkdirAll(oldBlobDir, 0o750); err != nil {
		t.Fatal(err)
	}
	blobContent := []byte("fake layer blob data")
	blobDigest := "sha256:ab1234567890abcdef"
	if err := os.WriteFile(filepath.Join(oldBlobDir, "ab1234567890abcdef"), blobContent, 0o644); err != nil {
		t.Fatal(err)
	}

	// Create and populate the DB.
	dbPath := filepath.Join(dataDir, "quay.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	if err := dbcore.InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}

	// Insert a test user, repo, manifest, tag, blob.
	ctx := t.Context()
	mustExec(t, db, `INSERT INTO "user" (uuid, username, email, verified, organization, robot, invoice_email,
		invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled)
		VALUES ('test-uuid', 'testns', 'test@test.com', 1, 0, 0, 0, 0, datetime('now'), 1209600, 1)`)

	mustExec(t, db, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, badge_token, trust_enabled, state)
		VALUES (1, 'testrepo', 1, 1, 'badge', 0, 0)`)

	manifestJSON := `{"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json"}`
	mustExec(t, db, `INSERT INTO manifest (repository_id, digest, media_type_id, manifest_bytes)
		VALUES (1, 'sha256:deadbeef1234567890', 1, ?)`, manifestJSON)

	mustExec(t, db, `INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, hidden, reversion, tag_kind_id, immutable)
		VALUES ('latest', 1, 1, 1000, 0, 0, 1, 0)`)

	mustExec(t, db, `INSERT INTO imagestorage (uuid, content_checksum, image_size, uploading, cas_path)
		VALUES ('blob-uuid', ?, 20, 0, 1)`, blobDigest)

	mustExec(t, db, `INSERT INTO manifestblob (repository_id, manifest_id, blob_id) VALUES (1, 1, 1)`)

	db.Close()

	// Run conversion.
	m := &Migrator{
		DataDir: dataDir,
		Out:     &bytes.Buffer{},
	}
	if err := m.convertStorage(ctx); err != nil {
		t.Fatalf("convertStorage: %v", err)
	}

	distRoot := filepath.Join(dataDir, "storage", "docker", "registry", "v2")

	// Verify blob was hard-linked.
	blobPath := filepath.Join(distRoot, "blobs", "sha256", "ab", "ab1234567890abcdef", "data")
	if _, err := os.Stat(blobPath); err != nil {
		t.Errorf("blob not found at distribution path: %s", blobPath)
	}

	// Verify manifest was written as blob.
	manifestBlobPath := filepath.Join(distRoot, "blobs", "sha256", "de", "deadbeef1234567890", "data")
	if _, err := os.Stat(manifestBlobPath); err != nil {
		t.Errorf("manifest blob not found: %s", manifestBlobPath)
	}

	// Verify tag link.
	tagLink := filepath.Join(distRoot, "repositories", "testns", "testrepo",
		"_manifests", "tags", "latest", "current", "link")
	linkContent, err := os.ReadFile(tagLink)
	if err != nil {
		t.Fatalf("tag link not found: %v", err)
	}
	if string(linkContent) != "sha256:deadbeef1234567890" {
		t.Errorf("tag link content: got %q, want %q", linkContent, "sha256:deadbeef1234567890")
	}

	// Verify revision link.
	revLink := filepath.Join(distRoot, "repositories", "testns", "testrepo",
		"_manifests", "revisions", "sha256", "deadbeef1234567890", "link")
	if _, err := os.Stat(revLink); err != nil {
		t.Errorf("revision link not found: %s", revLink)
	}

	// Verify layer link.
	layerLink := filepath.Join(distRoot, "repositories", "testns", "testrepo",
		"_layers", "sha256", "ab1234567890abcdef", "link")
	if _, err := os.Stat(layerLink); err != nil {
		t.Errorf("layer link not found: %s", layerLink)
	}

	// Verify old storage was cleaned up.
	if _, err := os.Stat(filepath.Join(dataDir, "storage", "sha256")); !os.IsNotExist(err) {
		t.Error("old sha256 directory should have been removed")
	}
}

func mustExec(t *testing.T, db *sql.DB, query string, args ...any) {
	t.Helper()
	if _, err := db.ExecContext(t.Context(), query, args...); err != nil {
		t.Fatalf("exec %q: %v", query[:min(len(query), 60)], err)
	}
}
