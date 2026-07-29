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
