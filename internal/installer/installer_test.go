package installer

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"errors"
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
			require.NoError(t, inst.upgrade(t.Context(), &Config{}, "localhost/quay:new", port))

			content, err := os.ReadFile(env.QuadletPath(quadletServiceName))
			require.NoError(t, err)
			assert.Contains(t, string(content), "Image=localhost/quay:new")
			assert.Contains(t, string(content), "PublishPort="+tt.wantPort+":8443")
			assert.Equal(t, []string{"stop:quay", "daemon-reload", "start:quay"}, services.calls)
		})
	}
}

func TestUpgradeInstallsReplacementTLS(t *testing.T) {
	dataDir := t.TempDir()
	oldCert, oldKey := generateTLSFiles(t, dataDir)
	oldCertData, err := os.ReadFile(oldCert)
	require.NoError(t, err)
	oldKeyData, err := os.ReadFile(oldKey)
	require.NoError(t, err)

	sourceDir := t.TempDir()
	newCert, newKey := generateTLSFiles(t, sourceDir)
	newCertData, err := os.ReadFile(newCert)
	require.NoError(t, err)
	newKeyData, err := os.ReadFile(newKey)
	require.NoError(t, err)
	require.NotEqual(t, oldCertData, newCertData)
	require.NotEqual(t, oldKeyData, newKeyData)

	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	quadlet := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, quadlet.Install(quadletServiceName, &system.QuadletSpec{
		Image:    "localhost/quay:old",
		DataDir:  dataDir,
		Hostname: "registry.example.com",
		Port:     "8443",
	}))
	services := &recordingServiceManager{}
	inst := &Installer{
		systemd: services,
		quadlet: quadlet,
		env:     env,
		fs:      system.OSFS{},
	}

	err = inst.upgrade(t.Context(), &Config{
		Hostname: "registry.example.com",
		DataDir:  dataDir,
		SSLCert:  newCert,
		SSLKey:   newKey,
	}, "localhost/quay:new", "8443")

	require.NoError(t, err)
	assert.Equal(t, newCertData, mustReadFile(t, filepath.Join(dataDir, "ssl.cert")))
	assert.Equal(t, newKeyData, mustReadFile(t, filepath.Join(dataDir, "ssl.key")))
	keyInfo, err := os.Stat(filepath.Join(dataDir, "ssl.key"))
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0o600), keyInfo.Mode().Perm())
	assert.Equal(t, []string{"stop:quay", "daemon-reload", "start:quay"}, services.calls)
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

func TestHealthTLSConfigSkipsOnlyHostnameVerification(t *testing.T) {
	serverDir := t.TempDir()
	serverCertPath, _ := generateTLSFiles(t, serverDir)
	serverCert, err := parseCertPEM(mustReadFile(t, serverCertPath))
	require.NoError(t, err)

	strictConfig, err := healthTLSConfig(mustReadFile(t, serverCertPath), false)
	require.NoError(t, err)
	assert.False(t, strictConfig.InsecureSkipVerify)
	assert.Nil(t, strictConfig.VerifyConnection)
	assert.Error(t, serverCert.VerifyHostname("127.0.0.1"))

	skipConfig, err := healthTLSConfig(mustReadFile(t, serverCertPath), true)
	require.NoError(t, err)
	assert.False(t, skipConfig.InsecureSkipVerify)
	assert.Equal(t, "registry.example.com", skipConfig.ServerName)
	_, err = serverCert.Verify(x509.VerifyOptions{
		Roots:     skipConfig.RootCAs,
		DNSName:   skipConfig.ServerName,
		KeyUsages: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	})
	require.NoError(t, err)

	untrustedDir := t.TempDir()
	untrustedCertPath, _ := generateTLSFiles(t, untrustedDir)
	untrustedConfig, err := healthTLSConfig(mustReadFile(t, untrustedCertPath), true)
	require.NoError(t, err)
	_, err = serverCert.Verify(x509.VerifyOptions{
		Roots:     untrustedConfig.RootCAs,
		DNSName:   untrustedConfig.ServerName,
		KeyUsages: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	})
	require.Error(t, err)
}

func TestCopyUserTLSReplacesPermissiveKeyWithSecureMode(t *testing.T) {
	dataDir := t.TempDir()
	generateTLSFiles(t, dataDir)
	require.NoError(t, os.Chmod(filepath.Join(dataDir, "ssl.key"), 0o644))

	sourceDir := t.TempDir()
	certPath, keyPath := generateTLSFiles(t, sourceDir)
	inst := &Installer{fs: system.OSFS{}}

	require.NoError(t, inst.copyUserTLS(&Config{
		Hostname: "registry.example.com",
		DataDir:  dataDir,
		SSLCert:  certPath,
		SSLKey:   keyPath,
	}))

	keyInfo, err := os.Stat(filepath.Join(dataDir, "ssl.key"))
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0o600), keyInfo.Mode().Perm())
	assert.Equal(t, mustReadFile(t, keyPath), mustReadFile(t, filepath.Join(dataDir, "ssl.key")))
}

func TestCopyUserTLSRejectsUnsafeDestinations(t *testing.T) {
	tests := []struct {
		name        string
		destination string
		setup       func(t *testing.T, path string)
	}{
		{
			name:        "certificate symlink",
			destination: "ssl.cert",
			setup: func(t *testing.T, path string) {
				t.Helper()
				target := filepath.Join(t.TempDir(), "target")
				require.NoError(t, os.WriteFile(target, []byte("unchanged"), 0o600))
				require.NoError(t, os.Symlink(target, path))
				t.Cleanup(func() {
					assert.Equal(t, []byte("unchanged"), mustReadFile(t, target))
				})
			},
		},
		{
			name:        "key directory",
			destination: "ssl.key",
			setup: func(t *testing.T, path string) {
				t.Helper()
				require.NoError(t, os.Mkdir(path, 0o700))
			},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			dataDir := t.TempDir()
			test.setup(t, filepath.Join(dataDir, test.destination))
			sourceDir := t.TempDir()
			certPath, keyPath := generateTLSFiles(t, sourceDir)
			inst := &Installer{fs: system.OSFS{}}

			err := inst.copyUserTLS(&Config{
				Hostname: "registry.example.com",
				DataDir:  dataDir,
				SSLCert:  certPath,
				SSLKey:   keyPath,
			})

			require.ErrorContains(t, err, "is not a regular file")
			info, statErr := os.Lstat(filepath.Join(dataDir, test.destination))
			require.NoError(t, statErr)
			if test.destination == "ssl.cert" {
				assert.NotZero(t, info.Mode()&os.ModeSymlink)
			} else {
				assert.True(t, info.IsDir())
			}
		})
	}
}

func TestCopyUserTLSRollsBackPairWhenKeyReplacementFails(t *testing.T) {
	dataDir := t.TempDir()
	oldCertPath, oldKeyPath := generateTLSFiles(t, dataDir)
	oldCert := mustReadFile(t, oldCertPath)
	oldKey := mustReadFile(t, oldKeyPath)

	sourceDir := t.TempDir()
	newCertPath, newKeyPath := generateTLSFiles(t, sourceDir)
	failingFS := &failKeyRenameFS{OSFS: system.OSFS{}, keyDestination: oldKeyPath}
	inst := &Installer{fs: failingFS}

	err := inst.copyUserTLS(&Config{
		Hostname: "registry.example.com",
		DataDir:  dataDir,
		SSLCert:  newCertPath,
		SSLKey:   newKeyPath,
	})

	require.ErrorContains(t, err, "replace ssl.key")
	assert.Equal(t, oldCert, mustReadFile(t, oldCertPath))
	assert.Equal(t, oldKey, mustReadFile(t, oldKeyPath))
	_, err = tls.X509KeyPair(mustReadFile(t, oldCertPath), mustReadFile(t, oldKeyPath))
	require.NoError(t, err)
	entries, err := os.ReadDir(dataDir)
	require.NoError(t, err)
	assert.Len(t, entries, 2)
}

type failKeyRenameFS struct {
	system.OSFS
	keyDestination string
}

func (fs *failKeyRenameFS) Rename(oldPath, newPath string) error {
	if newPath == fs.keyDestination && filepath.Base(oldPath) == "ssl.key" {
		return errors.New("injected key replacement failure")
	}
	return fs.OSFS.Rename(oldPath, newPath)
}

func generateTLSFiles(t *testing.T, dir string) (certPath, keyPath string) {
	t.Helper()
	certPath = filepath.Join(dir, "ssl.cert")
	keyPath = filepath.Join(dir, "ssl.key")
	require.NoError(t, certs.GenerateSelfSigned("registry.example.com", certPath, keyPath))
	return certPath, keyPath
}

func mustReadFile(t *testing.T, path string) []byte {
	t.Helper()
	data, err := os.ReadFile(path)
	require.NoError(t, err)
	return data
}
