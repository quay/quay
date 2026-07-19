package distribution

import (
	"context"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"reflect"
	"testing"
	"time"

	"golang.org/x/crypto/bcrypt"

	quayauth "github.com/quay/quay/internal/auth"
	registryauth "github.com/quay/quay/internal/registry/auth"
	_ "modernc.org/sqlite"
)

func setupTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	statements := []string{
		`CREATE TABLE "user" (id INTEGER PRIMARY KEY, uuid TEXT, username TEXT NOT NULL, password_hash TEXT, email TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0, organization INTEGER NOT NULL DEFAULT 0, robot INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1, last_accessed DATETIME)`,
		`CREATE TABLE visibility (id INTEGER PRIMARY KEY, name TEXT NOT NULL)`,
		`CREATE TABLE repository (id INTEGER PRIMARY KEY, namespace_user_id INTEGER, name TEXT NOT NULL, visibility_id INTEGER NOT NULL, kind_id INTEGER NOT NULL DEFAULT 1, state INTEGER NOT NULL DEFAULT 0)`,
		`CREATE TABLE role (id INTEGER PRIMARY KEY, name TEXT NOT NULL)`,
		`CREATE TABLE teamrole (id INTEGER PRIMARY KEY, name TEXT NOT NULL)`,
		`CREATE TABLE team (id INTEGER PRIMARY KEY, name TEXT NOT NULL, organization_id INTEGER NOT NULL, role_id INTEGER NOT NULL, description TEXT NOT NULL)`,
		`CREATE TABLE teammember (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, team_id INTEGER NOT NULL)`,
		`CREATE TABLE repositorypermission (id INTEGER PRIMARY KEY, team_id INTEGER, user_id INTEGER, repository_id INTEGER NOT NULL, role_id INTEGER NOT NULL)`,
		`CREATE TABLE repomirrorconfig (id INTEGER PRIMARY KEY, repository_id INTEGER NOT NULL, internal_robot_id INTEGER)`,
		`CREATE TABLE orgmirrorconfig (id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, internal_robot_id INTEGER)`,
		`CREATE TABLE orgmirrorrepository (id INTEGER PRIMARY KEY, org_mirror_config_id INTEGER NOT NULL, repository_id INTEGER)`,
		`CREATE TABLE robotaccounttoken (id INTEGER PRIMARY KEY, robot_account_id INTEGER NOT NULL, token TEXT NOT NULL, fully_migrated BOOLEAN DEFAULT 0 NOT NULL)`,
		`INSERT INTO visibility VALUES (1, 'public'), (2, 'private')`,
		`INSERT INTO role VALUES (1, 'read'), (2, 'write'), (3, 'admin')`,
		`INSERT INTO teamrole VALUES (1, 'admin'), (2, 'creator'), (3, 'member')`,
		`INSERT INTO "user" (id, uuid, username, email, organization, robot, enabled) VALUES
			(1, 'u-admin', 'admin', 'admin@example.com', 0, 0, 1),
			(2, 'org-acme', 'acme', 'acme@example.com', 1, 0, 1),
			(3, 'robot-reader', 'acme+reader', 'robot@example.com', 0, 1, 1),
			(4, 'robot-writer', 'acme+writer', 'robot@example.com', 0, 1, 1),
			(5, 'u-public', 'public', 'public@example.com', 0, 0, 1),
			(6, 'org-disabled', 'disabled', 'disabled@example.com', 1, 0, 0),
			(7, 'u-library', 'library', 'library@example.com', 0, 0, 1),
			(8, 'org-create', 'createorg', 'create@example.com', 1, 0, 1)`,
		`INSERT INTO repository (id, namespace_user_id, name, visibility_id, kind_id, state) VALUES
			(1, 5, 'publicrepo', 1, 1, 0),
			(2, 2, 'private', 2, 1, 0),
			(3, 5, 'deleted', 1, 1, 3),
			(4, 2, 'readonly', 2, 1, 1),
			(5, 2, 'application', 2, 2, 0),
			(6, 6, 'publicrepo', 1, 1, 0),
			(7, 7, 'busybox', 1, 1, 0),
			(8, 2, 'mirror', 2, 1, 2),
			(9, 2, 'orgmirror', 2, 1, 4)`,
		`INSERT INTO repositorypermission (id, user_id, repository_id, role_id) VALUES
			(1, 3, 2, 1), (2, 4, 2, 2), (3, 4, 4, 2), (4, 4, 5, 3),
			(5, 4, 8, 2), (6, 4, 9, 2)`,
		`INSERT INTO team (id, name, organization_id, role_id, description) VALUES
			(1, 'creators', 2, 2, ''), (2, 'createorg-creators', 8, 2, '')`,
		`INSERT INTO teammember (id, user_id, team_id) VALUES (1, 4, 1), (2, 4, 2)`,
		`INSERT INTO repomirrorconfig (id, repository_id, internal_robot_id) VALUES (1, 8, 4)`,
		`INSERT INTO orgmirrorconfig (id, organization_id, internal_robot_id) VALUES (1, 2, 4)`,
		`INSERT INTO orgmirrorrepository (id, org_mirror_config_id, repository_id) VALUES (1, 1, 9)`,
		`INSERT INTO robotaccounttoken (id, robot_account_id, token, fully_migrated) VALUES
			(1, 4, 'v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==', 1)`,
	}
	for _, statement := range statements {
		if _, err := db.ExecContext(t.Context(), statement); err != nil {
			t.Fatalf("exec %q: %v", statement, err)
		}
	}
	passwordHash, err := bcrypt.GenerateFromPassword([]byte("correct-password"), bcrypt.MinCost)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), `UPDATE "user" SET password_hash = ? WHERE username = 'admin'`, string(passwordHash)); err != nil {
		t.Fatal(err)
	}
	return db
}

func identity(principal *quayauth.Principal) registryauth.Identity {
	return registryauth.Identity{Subject: principal.Username, Principal: principal}
}

func userPrincipal(id int64, username string) *quayauth.Principal {
	return &quayauth.Principal{ID: id, Username: username, Kind: quayauth.PrincipalUser}
}

func robotPrincipal(id int64, username string) *quayauth.Principal {
	return &quayauth.Principal{ID: id, Username: username, Kind: quayauth.PrincipalRobot}
}

func resolveOne(t *testing.T, resolver *GrantResolver, principal registryauth.Identity, name string, actions ...string) []string {
	t.Helper()
	grants, err := resolver.Resolve(t.Context(), principal, []registryauth.Scope{{Type: "repository", Name: name, Actions: actions}})
	if err != nil {
		t.Fatal(err)
	}
	if len(grants) != 1 {
		t.Fatalf("grants = %#v", grants)
	}
	return grants[0].Actions
}

func TestGrantResolverDownscopesRepositoryActions(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	resolver, err := NewGrantResolver(db, GrantResolverConfig{})
	if err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name       string
		identity   registryauth.Identity
		repository string
		requested  []string
		want       []string
	}{
		{"anonymous public pull", registryauth.Identity{Subject: registryauth.AnonymousSubject, Anonymous: true}, "public/publicrepo", []string{"pull", "push"}, []string{"pull"}},
		{"anonymous private pull", registryauth.Identity{Subject: registryauth.AnonymousSubject, Anonymous: true}, "acme/private", []string{"pull"}, []string{}},
		{"reader pull", identity(robotPrincipal(3, "acme+reader")), "acme/private", []string{"pull", "push", "delete", "*"}, []string{"pull"}},
		{"writer pull push delete", identity(robotPrincipal(4, "acme+writer")), "acme/private", []string{"pull", "push", "delete"}, []string{"delete", "pull", "push"}},
		{"owner admin wildcard", identity(userPrincipal(2, "acme")), "acme/private", []string{"*"}, []string{"*"}},
		{"normal user denied", identity(userPrincipal(1, "admin")), "acme/private", []string{"pull", "push"}, []string{}},
		{"deleted denied", identity(userPrincipal(5, "public")), "public/deleted", []string{"pull", "push", "delete", "*"}, []string{}},
		{"disabled namespace denied", identity(userPrincipal(6, "disabled")), "disabled/publicrepo", []string{"pull", "push", "*"}, []string{}},
		{"application denied", identity(robotPrincipal(4, "acme+writer")), "acme/application", []string{"pull", "push", "*"}, []string{}},
		{"readonly push and admin denied", identity(robotPrincipal(4, "acme+writer")), "acme/readonly", []string{"push", "delete", "*"}, []string{}},
		{"library normalized", registryauth.Identity{Subject: registryauth.AnonymousSubject, Anonymous: true}, "library/busybox", []string{"pull"}, []string{"pull"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := resolveOne(t, resolver, tt.identity, tt.repository, tt.requested...)
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("actions = %#v, want %#v", got, tt.want)
			}
		})
	}
}

func TestGrantResolverMissingRepositoryIsSideEffectFree(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	resolver, err := NewGrantResolver(db, GrantResolverConfig{})
	if err != nil {
		t.Fatal(err)
	}
	creator := identity(robotPrincipal(4, "acme+writer"))
	got := resolveOne(t, resolver, creator, "createorg/newrepo", "pull", "push", "delete", "*")
	if want := []string{"pull", "push"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("actions = %#v, want %#v", got, want)
	}
	var count int
	if err := db.QueryRowContext(t.Context(), `SELECT COUNT(*) FROM repository WHERE name = 'newrepo'`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatalf("token issuance created %d repositories", count)
	}
	pullOnly := resolveOne(t, resolver, creator, "createorg/pullprobe", "pull")
	if want := []string{"pull"}; !reflect.DeepEqual(pullOnly, want) {
		t.Fatalf("pull-only actions = %#v, want %#v", pullOnly, want)
	}

	denied := resolveOne(t, resolver, identity(userPrincipal(1, "admin")), "createorg/other", "pull", "push")
	if len(denied) != 0 {
		t.Fatalf("denied actions = %#v", denied)
	}
}

func TestGrantResolverPreservesMirrorRobotRules(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	resolver, err := NewGrantResolver(db, GrantResolverConfig{})
	if err != nil {
		t.Fatal(err)
	}
	writer := identity(robotPrincipal(4, "acme+writer"))
	for _, repository := range []string{"acme/mirror", "acme/orgmirror"} {
		if got := resolveOne(t, resolver, writer, repository, "push"); !reflect.DeepEqual(got, []string{"push"}) {
			t.Fatalf("%s actions = %#v", repository, got)
		}
		if got := resolveOne(t, resolver, identity(userPrincipal(2, "acme")), repository, "push"); len(got) != 0 {
			t.Fatalf("%s owner actions = %#v", repository, got)
		}
	}
}

func TestGrantResolverCatalogGetsNoAccess(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	resolver, err := NewGrantResolver(db, GrantResolverConfig{})
	if err != nil {
		t.Fatal(err)
	}
	grants, err := resolver.Resolve(t.Context(), identity(userPrincipal(1, "admin")), []registryauth.Scope{{Type: "registry", Name: "catalog", Actions: []string{"*"}}})
	if err != nil {
		t.Fatal(err)
	}
	if len(grants) != 1 || len(grants[0].Actions) != 0 {
		t.Fatalf("grants = %#v", grants)
	}
}

func TestGrantResolverRejectsInvalidIdentity(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	resolver, err := NewGrantResolver(db, GrantResolverConfig{})
	if err != nil {
		t.Fatal(err)
	}
	_, err = resolver.Resolve(context.Background(), registryauth.Identity{Subject: "admin", Principal: "not-a-principal"}, nil)
	if err == nil {
		t.Fatal("expected invalid principal error")
	}
}

func TestTokenHandlerAcceptsExistingHumanAndMigratedRobotCredentials(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	resolver, err := NewGrantResolver(db, GrantResolverConfig{})
	if err != nil {
		t.Fatal(err)
	}
	verifier := quayauth.NewDatabaseVerifier(db, quayauth.DatabaseVerifierConfig{DatabaseSecretKey: "test1234"})
	signer, tokenVerifier, err := registryauth.NewES256Pair(registryauth.ES256Config{
		Issuer: registryauth.Issuer, Audience: "registry.example.com",
		MaxFresh: 10 * time.Minute, ClockSkew: 5 * time.Second,
	})
	if err != nil {
		t.Fatal(err)
	}
	handler, err := registryauth.NewHandler(registryauth.HandlerConfig{
		Service: "registry.example.com", LibraryNamespace: "library", AnonymousAccess: true,
		Lifetime: 5 * time.Minute, Signer: signer, ResolveGrants: resolver.Resolve,
		Authenticate: func(ctx context.Context, username, secret string) (registryauth.Identity, bool) {
			result := verifier.Verify(ctx, quayauth.Credentials{Username: username, Secret: secret})
			if !result.Authenticated {
				return registryauth.Identity{}, false
			}
			principal := result.Principal
			return registryauth.Identity{Subject: principal.Username, Principal: &principal}, true
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	for _, credentials := range []struct {
		name, username, password, subject string
		status                            int
	}{
		{"human", "admin", "correct-password", "admin", http.StatusOK},
		{"migrated robot", "acme+writer", "hello world", "acme+writer", http.StatusOK},
		{"invalid human", "admin", "wrong", "", http.StatusUnauthorized},
		{"invalid robot", "acme+writer", "wrong", "", http.StatusUnauthorized},
	} {
		t.Run(credentials.name, func(t *testing.T) {
			request := httptest.NewRequest(http.MethodGet,
				"/v2/auth?service="+url.QueryEscape("registry.example.com"), http.NoBody)
			request.SetBasicAuth(credentials.username, credentials.password)
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, request)
			if response.Code != credentials.status {
				t.Fatalf("status = %d, body = %s", response.Code, response.Body.String())
			}
			if credentials.status != http.StatusOK {
				return
			}
			var body struct {
				Token string `json:"token"`
			}
			if err := json.NewDecoder(response.Body).Decode(&body); err != nil {
				t.Fatal(err)
			}
			claims, err := tokenVerifier.Verify(body.Token)
			if err != nil {
				t.Fatal(err)
			}
			if claims.Subject != credentials.subject {
				t.Fatalf("subject = %q, want %q", claims.Subject, credentials.subject)
			}
		})
	}
}
