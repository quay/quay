package installer

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/certs"
	"github.com/quay/quay/internal/system"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUpgradeUsesEffectivePort(t *testing.T) {
	tests := []struct {
		name          string
		requestedPort string
		wantPort      string
	}{
		{
			name:          "explicit port replaces existing port",
			requestedPort: "10443",
			wantPort:      "10443",
		},
		{
			name:     "omitted port preserves existing port",
			wantPort: "9443",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
			quadlet := system.NewQuadletManager(system.OSFS{}, env)
			require.NoError(t, quadlet.Install(quadletServiceName, &system.QuadletSpec{
				Image:    "localhost/quay:old",
				DataDir:  "/var/lib/quay",
				Hostname: "registry.example.com",
				Port:     "9443",
			}))

			services := &recordingServiceManager{}
			inst := &Installer{
				systemd: services,
				quadlet: quadlet,
				env:     env,
			}

			port, err := inst.resolvePort(tt.requestedPort, true)
			require.NoError(t, err)
			require.Equal(t, tt.wantPort, port)
			require.NoError(t, inst.upgrade(t.Context(), "localhost/quay:new", port))

			content, err := os.ReadFile(env.QuadletPath(quadletServiceName))
			require.NoError(t, err)
			assert.Contains(t, string(content), "Image=localhost/quay:new")
			assert.Contains(t, string(content), "PublishPort="+tt.wantPort+":8443")
			assert.Equal(t, []string{"stop:quay", "daemon-reload", "start:quay"}, services.calls)
		})
	}
}

func TestResolvePortDefaultsFreshInstall(t *testing.T) {
	inst := &Installer{}

	port, err := inst.resolvePort("", false)

	require.NoError(t, err)
	assert.Equal(t, "8443", port)
}

func TestRunReportsQuadletPortResolutionErrors(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	quadlet := system.NewQuadletManager(system.OSFS{}, env)
	quadletPath := env.QuadletPath(quadletServiceName)
	require.NoError(t, os.MkdirAll(filepath.Dir(quadletPath), 0o755))
	require.NoError(t, os.WriteFile(quadletPath, []byte("[Container]\nImage=localhost/quay:test\n"), 0o600))

	inst := &Installer{quadlet: quadlet}
	err := inst.Run(t.Context(), &Config{})

	require.ErrorContains(t, err, "resolve port: determine existing port")
	assert.NotContains(t, err.Error(), "invalid port")
}

type recordingServiceManager struct {
	calls []string
}

func (r *recordingServiceManager) DaemonReload(context.Context) error {
	r.calls = append(r.calls, "daemon-reload")
	return nil
}

func (r *recordingServiceManager) Start(_ context.Context, service string) error {
	r.calls = append(r.calls, "start:"+service)
	return nil
}

func (r *recordingServiceManager) Stop(_ context.Context, service string) error {
	r.calls = append(r.calls, "stop:"+service)
	return nil
}

func (r *recordingServiceManager) EnableLinger(context.Context) error {
	return nil
}

var _ system.ServiceManager = (*recordingServiceManager)(nil)

func TestValidateSSLFlags(t *testing.T) {
	tests := []struct {
		name    string
		cert    string
		key     string
		wantErr bool
	}{
		{"both empty", "", "", false},
		{"both set", "/tmp/ssl.cert", "/tmp/ssl.key", false},
		{"cert only", "/tmp/ssl.cert", "", true},
		{"key only", "", "/tmp/ssl.key", true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateSSLFlags(tt.cert, tt.key)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateSSLFlags(%q, %q) error = %v, wantErr %v", tt.cert, tt.key, err, tt.wantErr)
			}
		})
	}
}

func TestVerifyCertHostname(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "ssl.cert")
	keyPath := filepath.Join(dir, "ssl.key")

	if err := certs.GenerateSelfSigned("myhost.example.com", certPath, keyPath); err != nil {
		t.Fatalf("generate cert: %v", err)
	}

	certData, err := os.ReadFile(certPath)
	if err != nil {
		t.Fatalf("read cert: %v", err)
	}

	cert, err := parseCertPEM(certData)
	if err != nil {
		t.Fatalf("parse cert: %v", err)
	}

	if err := verifyCertHostname(cert, "myhost.example.com"); err != nil {
		t.Errorf("expected hostname to match: %v", err)
	}

	if err := verifyCertHostname(cert, "wrong.example.com"); err == nil {
		t.Error("expected hostname mismatch error")
	}
}

func TestVerifyCertHostnameIP(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "ssl.cert")
	keyPath := filepath.Join(dir, "ssl.key")

	if err := certs.GenerateSelfSigned("192.168.1.100", certPath, keyPath); err != nil {
		t.Fatalf("generate cert: %v", err)
	}

	certData, err := os.ReadFile(certPath)
	if err != nil {
		t.Fatalf("read cert: %v", err)
	}

	cert, err := parseCertPEM(certData)
	if err != nil {
		t.Fatalf("parse cert: %v", err)
	}

	if err := verifyCertHostname(cert, "192.168.1.100"); err != nil {
		t.Errorf("expected IP to match: %v", err)
	}

	if err := verifyCertHostname(cert, "10.0.0.1"); err == nil {
		t.Error("expected IP mismatch error")
	}
}

func TestParseCertPEM(t *testing.T) {
	dir := t.TempDir()
	certPath := filepath.Join(dir, "ssl.cert")
	keyPath := filepath.Join(dir, "ssl.key")

	if err := certs.GenerateSelfSigned("test.example.com", certPath, keyPath); err != nil {
		t.Fatalf("generate cert: %v", err)
	}

	certData, err := os.ReadFile(certPath)
	if err != nil {
		t.Fatalf("read cert: %v", err)
	}

	cert, err := parseCertPEM(certData)
	if err != nil {
		t.Fatalf("parseCertPEM: %v", err)
	}

	if cert.Subject.CommonName != "test.example.com" {
		t.Errorf("CN = %q, want %q", cert.Subject.CommonName, "test.example.com")
	}
}

func TestParseCertPEM_Invalid(t *testing.T) {
	_, err := parseCertPEM([]byte("not a cert"))
	if err == nil {
		t.Error("expected error for invalid PEM")
	}
}
