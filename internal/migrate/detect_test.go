package migrate

import (
	"os"
	"path/filepath"
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

func TestExtractHostname(t *testing.T) {
	yaml := `AUTHENTICATION_TYPE: Database
SERVER_HOSTNAME: registry.example.com
SETUP_COMPLETE: true
DB_URI: sqlite:////sqlite/quay_sqlite.db
`
	hostname, err := extractHostname([]byte(yaml))
	if err != nil {
		t.Fatalf("extractHostname: %v", err)
	}
	if hostname != "registry.example.com" {
		t.Errorf("got %q, want %q", hostname, "registry.example.com")
	}
}

func TestExtractHostname_StripsPort(t *testing.T) {
	yaml := `SERVER_HOSTNAME: localhost:8443
`
	hostname, err := extractHostname([]byte(yaml))
	if err != nil {
		t.Fatalf("extractHostname: %v", err)
	}
	if hostname != "localhost" {
		t.Errorf("got %q, want %q", hostname, "localhost")
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
