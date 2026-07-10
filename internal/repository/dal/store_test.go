package dal

import (
	"database/sql"
	"errors"
	"testing"

	"github.com/quay/quay/internal/repository"

	_ "modernc.org/sqlite"
)

type fakeResult struct {
	rowsAffected    int64
	rowsAffectedErr error
}

var _ sql.Result = fakeResult{}

func (r fakeResult) LastInsertId() (int64, error) {
	return 0, nil
}

func (r fakeResult) RowsAffected() (int64, error) {
	return r.rowsAffected, r.rowsAffectedErr
}

func TestRequireRowsAffected(t *testing.T) {
	sentinelErr := errors.New("rows affected unavailable")

	for _, tc := range []struct {
		name    string
		result  sql.Result
		wantErr error
	}{
		{
			name:    "driver error",
			result:  fakeResult{rowsAffectedErr: sentinelErr},
			wantErr: sentinelErr,
		},
		{
			name:    "no rows",
			result:  fakeResult{rowsAffected: 0},
			wantErr: repository.ErrNotFound,
		},
		{
			name:   "changed rows",
			result: fakeResult{rowsAffected: 1},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			err := requireRowsAffected(tc.result)
			if !errors.Is(err, tc.wantErr) {
				t.Fatalf("err = %v, want %v", err, tc.wantErr)
			}
		})
	}
}

func setupStoreTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	db.SetMaxOpenConns(1)

	ctx := t.Context()
	statements := []string{
		`CREATE TABLE "user" (id INTEGER PRIMARY KEY, username VARCHAR(255) NOT NULL, enabled INTEGER NOT NULL DEFAULT 1)`,
		`CREATE TABLE visibility (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL)`,
		`CREATE TABLE repository (id INTEGER PRIMARY KEY, namespace_user_id INTEGER NOT NULL, name VARCHAR(255) NOT NULL, visibility_id INTEGER NOT NULL, kind_id INTEGER NOT NULL DEFAULT 1, state INTEGER NOT NULL DEFAULT 0)`,
		`INSERT INTO "user" (id, username, enabled) VALUES (1, 'disabled-org', 0), (2, 'enabled-org', 1)`,
		`INSERT INTO visibility (id, name) VALUES (1, 'public'), (2, 'private')`,
		`INSERT INTO repository (id, namespace_user_id, name, visibility_id, kind_id, state) VALUES (10, 1, 'publicrepo', 1, 1, 0), (11, 2, 'publicrepo', 1, 1, 0)`,
	}
	for _, stmt := range statements {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			t.Fatalf("exec %q: %v", stmt, err)
		}
	}
	return db
}

func TestStoreGetReturnsRepositoryForDisabledNamespace(t *testing.T) {
	db := setupStoreTestDB(t)
	t.Cleanup(func() { _ = db.Close() })

	store := NewStore(db)
	for _, tc := range []struct {
		name          string
		ref           repository.Ref
		wantID        int64
		wantNamespace bool
		wantNotFound  bool
	}{
		{
			name:          "disabled namespace",
			ref:           repository.Ref{Namespace: "disabled-org", Name: "publicrepo"},
			wantID:        10,
			wantNamespace: false,
		},
		{
			name:          "enabled namespace",
			ref:           repository.Ref{Namespace: "enabled-org", Name: "publicrepo"},
			wantID:        11,
			wantNamespace: true,
		},
		{
			name:         "missing namespace",
			ref:          repository.Ref{Namespace: "missing-org", Name: "publicrepo"},
			wantNotFound: true,
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			repo, err := store.Get(t.Context(), tc.ref)
			if tc.wantNotFound {
				if !errors.Is(err, repository.ErrNotFound) {
					t.Fatalf("Get err = %v, want ErrNotFound", err)
				}
				if repo != (repository.Repository{}) {
					t.Fatalf("repo = %#v, want zero value", repo)
				}
				return
			}
			if err != nil {
				t.Fatalf("Get: %v", err)
			}
			if repo.NamespaceEnabled != tc.wantNamespace {
				t.Fatalf("NamespaceEnabled = %v, want %v", repo.NamespaceEnabled, tc.wantNamespace)
			}
			if repo.ID != tc.wantID {
				t.Fatalf("ID = %d, want %d", repo.ID, tc.wantID)
			}
			if repo.Visibility != repository.VisibilityPublic {
				t.Fatalf("Visibility = %q, want public", repo.Visibility)
			}
		})
	}
}
