package migrate

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestParseUnitVolumes(t *testing.T) {
	unit := `[Unit]
Description=Quay App
After=quay-pod.service

[Service]
Type=simple
ExecStart=/usr/bin/podman run --name quay-app --pod=quay-pod \
  -v /home/user/quay-install/quay-config:/quay-registry/conf/stack:Z \
  -v sqlite-storage:/sqlite:Z \
  -v quay-storage:/datastorage:Z \
  registry.redhat.io/quay/quay-rhel8:v3.12.12 registry

[Install]
WantedBy=default.target
`
	vols := parseUnitVolumes(unit)

	if len(vols) != 3 {
		t.Fatalf("expected 3 volumes, got %d: %v", len(vols), vols)
	}

	want := map[string]string{
		"/quay-registry/conf/stack": "/home/user/quay-install/quay-config",
		"/sqlite":                   "sqlite-storage",
		"/datastorage":              "quay-storage",
	}
	for container, host := range want {
		got, ok := vols[container]
		if !ok {
			t.Errorf("missing mount for %s", container)
			continue
		}
		if got != host {
			t.Errorf("mount %s: got %q, want %q", container, got, host)
		}
	}
}

func TestSourceFromUnitDetectsKCSPostgres(t *testing.T) {
	for _, configMount := range []string{"/quay-registry/conf/stack", "/conf/stack"} {
		t.Run(configMount, func(t *testing.T) {
			unitDir := t.TempDir()
			configDir := t.TempDir()
			if err := os.WriteFile(filepath.Join(configDir, "config.yaml"), []byte("DB_URI: postgresql://user:password@quay-postgres/quay\nSERVER_HOSTNAME: registry.example.com\n"), 0o600); err != nil {
				t.Fatal(err)
			}
			writePostgresUnits(t, unitDir)

			runner := &topologyRunner{outputs: map[string]string{
				"podman inspect quay-postgres --format {{.Pod}} {{.NetworkSettings.SandboxKey}}": "pod-id /run/user/1000/netns/quay",
				"podman pod inspect quay-pod --format {{.Id}}":                                   "pod-id",
				"podman inspect quay-app --format {{.Pod}}":                                      "pod-id",
			}}
			appUnit := fmt.Sprintf("ExecStart=/usr/bin/podman run --name quay-app --pod=quay-pod -v %s:%s:Z", configDir, configMount)
			src, err := (&Migrator{Runner: runner}).sourceFromUnit(t.Context(), appUnit, scopeUser, unitDir)
			if err != nil {
				t.Fatalf("sourceFromUnit: %v", err)
			}
			if src.DatabaseKind != databasePostgres {
				t.Errorf("database kind = %q, want %q", src.DatabaseKind, databasePostgres)
			}
			if src.ConfigDir != configDir {
				t.Errorf("config dir = %q, want %q", src.ConfigDir, configDir)
			}
			if src.DBPath != "" {
				t.Errorf("PostgreSQL DB path = %q, want empty", src.DBPath)
			}
			if src.PodSandboxKey != "/run/user/1000/netns/quay" {
				t.Errorf("sandbox key = %q", src.PodSandboxKey)
			}
		})
	}
}

func TestSourceFromUnitUsesExplicitConfigOverride(t *testing.T) {
	unitDir := t.TempDir()
	configDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(configDir, "config.yaml"), []byte("DB_URI: postgresql://user:password@quay-postgres/quay\nSERVER_HOSTNAME: registry.example.com\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	writePostgresUnits(t, unitDir)
	runner := &topologyRunner{outputs: map[string]string{
		"podman inspect quay-postgres --format {{.Pod}} {{.NetworkSettings.SandboxKey}}": "pod-id /run/user/1000/netns/quay",
		"podman pod inspect quay-pod --format {{.Id}}":                                   "pod-id",
		"podman inspect quay-app --format {{.Pod}}":                                      "pod-id",
	}}
	m := &Migrator{Runner: runner, Source: OMRSource{ConfigDir: configDir}}
	src, err := m.sourceFromUnit(t.Context(), "ExecStart=/usr/bin/podman run --name quay-app --pod=quay-pod", scopeUser, unitDir)
	if err != nil {
		t.Fatal(err)
	}
	if src.DatabaseKind != databasePostgres || src.ConfigDir != configDir {
		t.Fatalf("source = %+v", src)
	}
}

func TestDetectPostgresTopologyRejectsWrongPodOrMissingSandbox(t *testing.T) {
	for _, tc := range []struct {
		name            string
		containerOutput string
		appPodID        string
		want            string
	}{
		{name: "wrong postgres pod", containerOutput: "different-pod /run/netns/quay", appPodID: "pod-id", want: "quay-postgres container is not in quay-pod"},
		{name: "wrong app pod", containerOutput: "pod-id /run/netns/quay", appPodID: "different-pod", want: "quay-app container is not in quay-pod"},
		{name: "missing sandbox", containerOutput: "pod-id", appPodID: "pod-id", want: "has no sandbox key"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			unitDir := t.TempDir()
			writePostgresUnits(t, unitDir)
			runner := &topologyRunner{outputs: map[string]string{
				"podman inspect quay-postgres --format {{.Pod}} {{.NetworkSettings.SandboxKey}}": tc.containerOutput,
				"podman pod inspect quay-pod --format {{.Id}}":                                   "pod-id",
				"podman inspect quay-app --format {{.Pod}}":                                      tc.appPodID,
			}}
			_, err := (&Migrator{Runner: runner}).detectPostgresTopology(t.Context(), unitDir)
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("detectPostgresTopology error = %v, want %q", err, tc.want)
			}
		})
	}
}

func TestExtractDatabaseKind(t *testing.T) {
	for _, tc := range []struct {
		name string
		uri  string
		want string
	}{
		{name: "sqlite", uri: "sqlite:////sqlite/quay_sqlite.db", want: databaseSQLite},
		{name: "postgres", uri: "postgresql://user:password@quay-postgres/quay", want: databasePostgres},
		{name: "postgres explicit port", uri: "postgresql://user:password@quay-postgres:5432/quay", want: databasePostgres},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := extractDatabaseKind([]byte("DB_URI: " + tc.uri + "\n"))
			if err != nil {
				t.Fatalf("extractDatabaseKind: %v", err)
			}
			if got != tc.want {
				t.Errorf("database kind = %q, want %q", got, tc.want)
			}
		})
	}
}

func TestExtractDatabaseKindRejectsInvalidPostgresWithoutLeakingPassword(t *testing.T) {
	const secret = "do-not-print-this-secret"
	for _, tc := range []struct {
		name    string
		uri     string
		wantErr string
	}{
		{name: "wrong host", uri: "postgresql://user:" + secret + "@other-postgres/quay", wantErr: `DB_URI host must be "quay-postgres"`},
		{name: "wrong scheme", uri: "mysql://user:" + secret + "@quay-postgres/quay", wantErr: `unsupported DB_URI scheme "mysql"`},
		{name: "missing user", uri: "postgresql://:" + secret + "@quay-postgres/quay", wantErr: "DB_URI is missing username"},
		{name: "missing password", uri: "postgresql://user@quay-postgres/quay", wantErr: "DB_URI is missing password"},
		{name: "wrong port", uri: "postgresql://user:" + secret + "@quay-postgres:5433/quay", wantErr: `DB_URI port must be 5432, got "5433"`},
		{name: "wrong db path", uri: "postgresql://user:" + secret + "@quay-postgres/otherdb", wantErr: `DB_URI database path must be "/quay", got "/otherdb"`},
		{name: "query parameters", uri: "postgresql://user:" + secret + "@quay-postgres/quay?sslmode=disable", wantErr: "DB_URI contains unsupported query parameters"},
		{name: "fragment", uri: "postgresql://user:" + secret + "@quay-postgres/quay#frag", wantErr: "DB_URI contains unsupported fragment"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			_, err := extractDatabaseKind([]byte("DB_URI: " + tc.uri + "\n"))
			if err == nil {
				t.Fatalf("extractDatabaseKind unexpectedly succeeded for %s", tc.name)
			}
			if !strings.Contains(err.Error(), tc.wantErr) {
				t.Errorf("error = %q, want substring %q", err.Error(), tc.wantErr)
			}
			if strings.Contains(err.Error(), secret) {
				t.Errorf("error leaked password: %v", err)
			}
		})
	}
}

func writePostgresUnits(t *testing.T, unitDir string) {
	t.Helper()
	postgresUnit := "ExecStart=/usr/bin/podman run --name quay-postgres --pod=quay-pod image\n"
	if err := os.WriteFile(filepath.Join(unitDir, "quay-postgres.service"), []byte(postgresUnit), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(unitDir, "quay-pod.service"), []byte("[Service]\n"), 0o600); err != nil {
		t.Fatal(err)
	}
}

type topologyRunner struct {
	outputs map[string]string
}

func (*topologyRunner) Run(context.Context, string, ...string) error { return nil }

func (r *topologyRunner) Output(_ context.Context, name string, args ...string) (string, error) {
	command := name + " " + strings.Join(args, " ")
	output, ok := r.outputs[command]
	if !ok {
		return "", fmt.Errorf("unexpected command: %s", command)
	}
	return output, nil
}

func TestExtractHostname(t *testing.T) {
	yaml := `AUTHENTICATION_TYPE: Database
SERVER_HOSTNAME: registry.example.com
SETUP_COMPLETE: true
DB_URI: sqlite:////sqlite/quay_sqlite.db
`
	hostname, port, err := extractHostname([]byte(yaml))
	if err != nil {
		t.Fatalf("extractHostname: %v", err)
	}
	if hostname != "registry.example.com" {
		t.Errorf("hostname: got %q, want %q", hostname, "registry.example.com")
	}
	if port != "" {
		t.Errorf("port: got %q, want empty (no port in source)", port)
	}
}

func TestExtractHostname_SplitsPort(t *testing.T) {
	yaml := `SERVER_HOSTNAME: localhost:8443
`
	hostname, port, err := extractHostname([]byte(yaml))
	if err != nil {
		t.Fatalf("extractHostname: %v", err)
	}
	if hostname != "localhost" {
		t.Errorf("hostname: got %q, want %q", hostname, "localhost")
	}
	if port != "8443" {
		t.Errorf("port: got %q, want %q", port, "8443")
	}
}

func TestExtractHostname_CustomPort(t *testing.T) {
	yaml := `SERVER_HOSTNAME: myhost:9443
`
	hostname, port, err := extractHostname([]byte(yaml))
	if err != nil {
		t.Fatalf("extractHostname: %v", err)
	}
	if hostname != "myhost" {
		t.Errorf("hostname: got %q, want %q", hostname, "myhost")
	}
	if port != "9443" {
		t.Errorf("port: got %q, want %q", port, "9443")
	}
}

func TestDetectRootCADir(t *testing.T) {
	root := t.TempDir()
	configDir := filepath.Join(root, "quay-config")
	caDir := filepath.Join(root, "quay-rootCA")
	if err := os.MkdirAll(configDir, 0o750); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(caDir, 0o750); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(caDir, "rootCA.pem"), []byte("fake-ca"), 0o644); err != nil {
		t.Fatal(err)
	}

	got := detectRootCADir(configDir)
	if got != caDir {
		t.Errorf("got %q, want %q", got, caDir)
	}
}

func TestDetectRootCADir_Missing(t *testing.T) {
	root := t.TempDir()
	configDir := filepath.Join(root, "quay-config")
	if err := os.MkdirAll(configDir, 0o750); err != nil {
		t.Fatal(err)
	}

	got := detectRootCADir(configDir)
	if got != "" {
		t.Errorf("got %q, want empty when rootCA.pem does not exist", got)
	}
}

func TestFindImageArchive(t *testing.T) {
	dir := t.TempDir()
	tarPath := filepath.Join(dir, "quay-mirror.tar")
	if err := os.WriteFile(tarPath, []byte("fake-tar"), 0o644); err != nil {
		t.Fatal(err)
	}

	got, err := findImageArchive(dir)
	if err != nil {
		t.Fatalf("findImageArchive: %v", err)
	}
	if got != tarPath {
		t.Errorf("got %q, want %q", got, tarPath)
	}
}

func TestFindImageArchive_MultipleTars(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{"a.tar", "b.tar"} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	_, err := findImageArchive(dir)
	if err == nil {
		t.Error("expected error for multiple tar files")
	}
}
