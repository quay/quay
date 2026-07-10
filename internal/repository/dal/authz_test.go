package dal

import (
	"database/sql"
	"testing"

	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/repository"

	_ "modernc.org/sqlite"
)

func setupAuthzTestDB(t *testing.T) *sql.DB {
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
		`CREATE TABLE repository (id INTEGER PRIMARY KEY, namespace_user_id INTEGER NOT NULL, name VARCHAR(255) NOT NULL, visibility_id INTEGER NOT NULL, state INTEGER NOT NULL DEFAULT 0)`,
		`CREATE TABLE role (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL)`,
		`CREATE TABLE teamrole (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL)`,
		`CREATE TABLE team (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL, organization_id INTEGER NOT NULL, role_id INTEGER NOT NULL, description TEXT NOT NULL)`,
		`CREATE TABLE teammember (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, team_id INTEGER NOT NULL)`,
		`CREATE TABLE repositorypermission (id INTEGER PRIMARY KEY, team_id INTEGER, user_id INTEGER, repository_id INTEGER NOT NULL, role_id INTEGER NOT NULL)`,
		`CREATE TABLE repomirrorconfig (id INTEGER PRIMARY KEY, repository_id INTEGER NOT NULL, internal_robot_id INTEGER)`,
		`CREATE TABLE orgmirrorconfig (id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, internal_robot_id INTEGER NOT NULL)`,
		`CREATE TABLE orgmirrorrepository (id INTEGER PRIMARY KEY, org_mirror_config_id INTEGER NOT NULL, repository_id INTEGER NOT NULL, repository_name VARCHAR(255) NOT NULL)`,
		`INSERT INTO "user" (id, username, enabled) VALUES (1, 'acme', 1), (2, 'alice', 1), (3, 'acme+reader', 1), (4, 'acme+writer', 1), (5, 'acme+admin', 1), (6, 'acme+teamrobot', 1), (7, 'acme+orgadmin', 1), (8, 'acme+creator', 1), (9, 'disabled-org', 0), (10, 'disabled-org+creator', 1), (11, 'acme+mirror', 1), (12, 'acme+orgmirror', 1), (13, 'acme+wrongmirror', 1), (15, 'plain', 1), (16, 'plain+creator', 1)`,
		`INSERT INTO visibility (id, name) VALUES (1, 'public'), (2, 'private')`,
		`INSERT INTO repository (id, namespace_user_id, name, visibility_id, state) VALUES (10, 1, 'private', 2, 0), (11, 1, 'public', 1, 0), (12, 9, 'public', 1, 0), (13, 1, 'mirror', 2, 2), (14, 1, 'orgmirror', 2, 4), (15, 1, 'deleted', 1, 3)`,
		`INSERT INTO role (id, name) VALUES (1, 'read'), (2, 'write'), (3, 'admin')`,
		`INSERT INTO teamrole (id, name) VALUES (1, 'admin'), (2, 'creator'), (3, 'member')`,
		`INSERT INTO repositorypermission (id, user_id, repository_id, role_id) VALUES (1, 3, 10, 1), (2, 4, 10, 2), (3, 5, 10, 3)`,
		`INSERT INTO team (id, name, organization_id, role_id, description) VALUES (20, 'writers', 1, 3, ''), (21, 'owners', 1, 1, ''), (22, 'creators', 1, 2, ''), (23, 'disabled-creators', 9, 2, ''), (24, 'plain-creators', 15, 2, '')`,
		`INSERT INTO teammember (id, user_id, team_id) VALUES (30, 6, 20), (31, 7, 21), (32, 8, 22), (33, 10, 23), (34, 16, 24)`,
		`INSERT INTO repositorypermission (id, team_id, repository_id, role_id) VALUES (4, 20, 10, 2)`,
		`INSERT INTO repomirrorconfig (id, repository_id, internal_robot_id) VALUES (40, 13, 11)`,
		`INSERT INTO orgmirrorconfig (id, organization_id, internal_robot_id) VALUES (50, 1, 12)`,
		`INSERT INTO orgmirrorrepository (id, org_mirror_config_id, repository_id, repository_name) VALUES (60, 50, 14, 'orgmirror')`,
	}
	for _, stmt := range statements {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			t.Fatalf("exec %q: %v", stmt, err)
		}
	}
	return db
}

func TestAuthorizerCanPullAndPushRepository(t *testing.T) {
	db := setupAuthzTestDB(t)
	t.Cleanup(func() { _ = db.Close() })

	privateRepo := repository.Repository{
		ID:               10,
		Ref:              repository.Ref{Namespace: "acme", Name: "private"},
		Visibility:       repository.VisibilityPrivate,
		State:            repository.StateNormal,
		KindID:           repository.KindImage,
		NamespaceEnabled: true,
	}
	publicRepo := repository.Repository{
		ID:               11,
		Ref:              repository.Ref{Namespace: "acme", Name: "public"},
		Visibility:       repository.VisibilityPublic,
		State:            repository.StateNormal,
		KindID:           repository.KindImage,
		NamespaceEnabled: true,
	}
	deletedPublicRepo := repository.Repository{
		ID:               15,
		Ref:              repository.Ref{Namespace: "acme", Name: "deleted"},
		Visibility:       repository.VisibilityPublic,
		State:            repository.StateMarkedForDeletion,
		KindID:           repository.KindImage,
		NamespaceEnabled: true,
	}
	disabledNamespacePublicRepo := repository.Repository{
		ID:         12,
		Ref:        repository.Ref{Namespace: "disabled-org", Name: "public"},
		Visibility: repository.VisibilityPublic,
		State:      repository.StateNormal,
		KindID:     repository.KindImage,
	}
	mirrorRepo := repository.Repository{
		ID:               13,
		Ref:              repository.Ref{Namespace: "acme", Name: "mirror"},
		Visibility:       repository.VisibilityPrivate,
		State:            repository.StateMirror,
		KindID:           repository.KindImage,
		NamespaceEnabled: true,
	}
	orgMirrorRepo := repository.Repository{
		ID:               14,
		Ref:              repository.Ref{Namespace: "acme", Name: "orgmirror"},
		Visibility:       repository.VisibilityPrivate,
		State:            repository.StateOrgMirror,
		KindID:           repository.KindImage,
		NamespaceEnabled: true,
	}

	tests := []struct {
		name      string
		cfg       AuthorizerConfig
		principal *auth.Principal
		repo      repository.Repository
		wantPull  bool
		wantPush  bool
	}{
		{
			name:      "namespace owner can pull and push private repo",
			principal: &auth.Principal{ID: 1, Username: "acme", Kind: auth.PrincipalUser},
			repo:      privateRepo,
			wantPull:  true,
			wantPush:  true,
		},
		{
			name:      "robot with direct read can pull but not push private repo",
			principal: &auth.Principal{ID: 3, Username: "acme+reader", Kind: auth.PrincipalRobot},
			repo:      privateRepo,
			wantPull:  true,
		},
		{
			name:      "robot with direct write can pull and push private repo",
			principal: &auth.Principal{ID: 4, Username: "acme+writer", Kind: auth.PrincipalRobot},
			repo:      privateRepo,
			wantPull:  true,
			wantPush:  true,
		},
		{
			name:      "robot with direct admin can pull and push private repo",
			principal: &auth.Principal{ID: 5, Username: "acme+admin", Kind: auth.PrincipalRobot},
			repo:      privateRepo,
			wantPull:  true,
			wantPush:  true,
		},
		{
			name:      "robot with team write can pull and push private repo",
			principal: &auth.Principal{ID: 6, Username: "acme+teamrobot", Kind: auth.PrincipalRobot},
			repo:      privateRepo,
			wantPull:  true,
			wantPush:  true,
		},
		{
			name:      "robot with org admin team membership can pull and push private repo",
			principal: &auth.Principal{ID: 7, Username: "acme+orgadmin", Kind: auth.PrincipalRobot},
			repo:      privateRepo,
			wantPull:  true,
			wantPush:  true,
		},
		{
			name:      "unrelated robot cannot pull or push private repo",
			principal: &auth.Principal{ID: 8, Username: "acme+other", Kind: auth.PrincipalRobot},
			repo:      privateRepo,
		},
		{
			name:      "authenticated user without permission can pull public repo but cannot push",
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			repo:      publicRepo,
			wantPull:  true,
		},
		{
			name:      "authenticated user cannot pull deleted public repo",
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			repo:      deletedPublicRepo,
		},
		{
			name:      "disabled namespace public repo cannot be pulled",
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			repo:      disabledNamespacePublicRepo,
		},
		{
			name:      "writer cannot push read-only repo",
			principal: &auth.Principal{ID: 4, Username: "acme+writer", Kind: auth.PrincipalRobot},
			repo: repository.Repository{
				ID:               privateRepo.ID,
				Ref:              privateRepo.Ref,
				Visibility:       privateRepo.Visibility,
				State:            1,
				KindID:           privateRepo.KindID,
				NamespaceEnabled: privateRepo.NamespaceEnabled,
			},
			wantPull: true,
		},
		{
			name:      "configured mirror robot can push mirror repo",
			principal: &auth.Principal{ID: 11, Username: "acme+mirror", Kind: auth.PrincipalRobot},
			repo:      mirrorRepo,
			wantPush:  true,
		},
		{
			name:      "non-mirror robot cannot push mirror repo",
			principal: &auth.Principal{ID: 13, Username: "acme+wrongmirror", Kind: auth.PrincipalRobot},
			repo:      mirrorRepo,
		},
		{
			name:      "configured org mirror robot can push org mirror repo",
			principal: &auth.Principal{ID: 12, Username: "acme+orgmirror", Kind: auth.PrincipalRobot},
			repo:      orgMirrorRepo,
			wantPush:  true,
		},
		{
			name:      "repo mirror robot cannot push org mirror repo",
			principal: &auth.Principal{ID: 11, Username: "acme+mirror", Kind: auth.PrincipalRobot},
			repo:      orgMirrorRepo,
		},
		{
			name: "configured superuser cannot push mirror repo",
			cfg: AuthorizerConfig{
				SuperUsers:           []string{"super"},
				SuperUsersFullAccess: true,
			},
			principal: &auth.Principal{ID: 99, Username: "super", Kind: auth.PrincipalUser},
			repo:      mirrorRepo,
			wantPull:  true,
		},
		{
			name:      "anonymous can pull public repo",
			principal: auth.AnonymousPrincipal(),
			repo:      publicRepo,
			wantPull:  true,
		},
		{
			name:      "anonymous cannot pull or push private repo",
			principal: auth.AnonymousPrincipal(),
			repo:      privateRepo,
		},
		{
			name:      "anonymous cannot push public repo",
			principal: auth.AnonymousPrincipal(),
			repo:      publicRepo,
			wantPull:  true,
		},
		{
			name: "configured superuser with full access can pull and push",
			cfg: AuthorizerConfig{
				SuperUsers:           []string{"super"},
				SuperUsersFullAccess: true,
			},
			principal: &auth.Principal{ID: 99, Username: "super", Kind: auth.PrincipalUser},
			repo:      privateRepo,
			wantPull:  true,
			wantPush:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			authorizer := NewAuthorizer(db, tt.cfg)

			gotPull, err := authorizer.CanPullRepository(t.Context(), tt.principal, &tt.repo)
			if err != nil {
				t.Fatalf("CanPullRepository: %v", err)
			}
			if gotPull != tt.wantPull {
				t.Fatalf("CanPullRepository = %v, want %v", gotPull, tt.wantPull)
			}

			gotPush, err := authorizer.CanPushRepository(t.Context(), tt.principal, &tt.repo)
			if err != nil {
				t.Fatalf("CanPushRepository: %v", err)
			}
			if gotPush != tt.wantPush {
				t.Fatalf("CanPushRepository = %v, want %v", gotPush, tt.wantPush)
			}
		})
	}
}

func TestAuthorizerQueriesRequireEnabledNamespaceForOwnerAccess(t *testing.T) {
	db := setupAuthzTestDB(t)
	t.Cleanup(func() { _ = db.Close() })

	queries := daldb.New(db)
	for _, tc := range []struct {
		name string
		fn   func() (int64, error)
	}{
		{
			name: "pull",
			fn: func() (int64, error) {
				return queries.UserCanPullRepository(t.Context(), daldb.UserCanPullRepositoryParams{
					RepositoryID: 12,
					Username:     "disabled-org",
					UserID:       sql.NullInt64{Int64: 9, Valid: true},
				})
			},
		},
		{
			name: "push",
			fn: func() (int64, error) {
				return queries.UserCanPushRepository(t.Context(), daldb.UserCanPushRepositoryParams{
					RepositoryID: 12,
					Username:     "disabled-org",
					UserID:       sql.NullInt64{Int64: 9, Valid: true},
				})
			},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			allowed, err := tc.fn()
			if err != nil {
				t.Fatalf("%s query: %v", tc.name, err)
			}
			if allowed != 0 {
				t.Fatalf("%s allowed = %d, want 0", tc.name, allowed)
			}
		})
	}
}

func TestAuthorizerCanCreateRepository(t *testing.T) {
	db := setupAuthzTestDB(t)
	t.Cleanup(func() { _ = db.Close() })

	tests := []struct {
		name      string
		cfg       AuthorizerConfig
		principal *auth.Principal
		namespace string
		want      bool
	}{
		{
			name:      "namespace owner cannot push-create in org mirrored namespace",
			principal: &auth.Principal{ID: 1, Username: "acme", Kind: auth.PrincipalUser},
			namespace: "acme",
		},
		{
			name:      "creator team member cannot push-create in org mirrored namespace",
			principal: &auth.Principal{ID: 8, Username: "acme+creator", Kind: auth.PrincipalRobot},
			namespace: "acme",
		},
		{
			name:      "namespace owner can create in non-mirrored namespace",
			principal: &auth.Principal{ID: 15, Username: "plain", Kind: auth.PrincipalUser},
			namespace: "plain",
			want:      true,
		},
		{
			name:      "creator team member can create in non-mirrored namespace",
			principal: &auth.Principal{ID: 16, Username: "plain+creator", Kind: auth.PrincipalRobot},
			namespace: "plain",
			want:      true,
		},
		{
			name:      "org mirror robot cannot push-create in org mirrored namespace",
			principal: &auth.Principal{ID: 12, Username: "acme+orgmirror", Kind: auth.PrincipalRobot},
			namespace: "acme",
		},
		{
			name: "superuser cannot push-create in org mirrored namespace",
			cfg: AuthorizerConfig{
				SuperUsers:           []string{"alice"},
				SuperUsersFullAccess: true,
			},
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			namespace: "acme",
		},
		{
			name:      "disabled namespace creator cannot create",
			principal: &auth.Principal{ID: 10, Username: "disabled-org+creator", Kind: auth.PrincipalRobot},
			namespace: "disabled-org",
		},
		{
			name: "superuser cannot create in disabled namespace",
			cfg: AuthorizerConfig{
				SuperUsers:           []string{"alice"},
				SuperUsersFullAccess: true,
			},
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			namespace: "disabled-org",
		},
		{
			name: "superuser can create missing namespace",
			cfg: AuthorizerConfig{
				SuperUsers:           []string{"alice"},
				SuperUsersFullAccess: true,
			},
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			namespace: "missing",
			want:      true,
		},
		{
			name:      "unrelated user cannot create",
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			namespace: "acme",
		},
		{
			name:      "missing namespace denies create without error",
			principal: &auth.Principal{ID: 2, Username: "alice", Kind: auth.PrincipalUser},
			namespace: "missing",
		},
		{
			name:      "anonymous cannot create",
			principal: auth.AnonymousPrincipal(),
			namespace: "acme",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			authorizer := NewAuthorizer(db, tt.cfg)

			got, err := authorizer.CanCreateRepository(t.Context(), tt.principal, tt.namespace)
			if err != nil {
				t.Fatalf("CanCreateRepository: %v", err)
			}
			if got != tt.want {
				t.Fatalf("CanCreateRepository = %v, want %v", got, tt.want)
			}
		})
	}
}
