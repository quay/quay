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
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/system"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"golang.org/x/crypto/bcrypt"
)

func TestInitializeCreatesCustomAdminSecurely(t *testing.T) {
	dataDir := t.TempDir()
	require.NoError(t, Initialize(t.Context(), &Config{
		DataDir:         dataDir,
		Hostname:        "registry.example.com",
		InitUser:        "custom-admin",
		InitPassword:    "  chosen password  ",
		InitPasswordSet: true,
	}))

	db, err := dbcore.OpenSQLite(filepath.Join(dataDir, "quay.db"))
	require.NoError(t, err)
	defer db.Close()
	user, err := daldb.New(db).GetUserByUsername(t.Context(), "custom-admin")
	require.NoError(t, err)
	require.NoError(t, bcrypt.CompareHashAndPassword(
		[]byte(user.PasswordHash.String),
		[]byte("  chosen password  "),
	))

	passwordPath := filepath.Join(dataDir, "auth", "admin-password")
	assert.Equal(t, []byte("  chosen password  "), mustReadFile(t, passwordPath))
	passwordInfo, err := os.Stat(passwordPath)
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0o600), passwordInfo.Mode().Perm())
	authInfo, err := os.Stat(filepath.Dir(passwordPath))
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0o700), authInfo.Mode().Perm())
}

func TestInitializeIsIdempotentForExistingDatabase(t *testing.T) {
	dataDir := t.TempDir()
	first := &Config{
		DataDir:         dataDir,
		InitUser:        "first-admin",
		InitPassword:    "first-password",
		InitPasswordSet: true,
	}
	require.NoError(t, Initialize(t.Context(), first))
	passwordPath := filepath.Join(dataDir, "auth", "admin-password")
	originalCredential := mustReadFile(t, passwordPath)

	require.NoError(t, Initialize(t.Context(), &Config{
		DataDir:  dataDir,
		InitUser: "second-admin",
	}))
	assert.Equal(t, originalCredential, mustReadFile(t, passwordPath))

	err := Initialize(t.Context(), &Config{
		DataDir:         dataDir,
		InitUser:        "first-admin",
		InitPassword:    "replacement-password",
		InitPasswordSet: true,
	})
	require.ErrorContains(t, err, "registry is already initialized")
	require.ErrorContains(t, err, "supplied password was not applied")
	assert.Equal(t, originalCredential, mustReadFile(t, passwordPath))

	db, err := dbcore.OpenSQLite(filepath.Join(dataDir, "quay.db"))
	require.NoError(t, err)
	defer db.Close()
	queries := daldb.New(db)
	_, err = queries.GetUserByUsername(t.Context(), "first-admin")
	require.NoError(t, err)
	_, err = queries.GetUserByUsername(t.Context(), "second-admin")
	require.Error(t, err)
}

func TestUpgradePreservesConfigBasedServeCommand(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	quadlet := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, quadlet.Install(quadletServiceName, &system.QuadletSpec{
		Image:      "localhost/quay:old",
		DataDir:    "/var/lib/quay",
		Hostname:   "registry.example.com",
		Port:       "8443",
		ConfigPath: "/data/config.yaml",
	}))
	services := &recordingServiceManager{}
	inst := &Installer{
		systemd: services,
		quadlet: quadlet,
		env:     env,
		fs:      system.OSFS{},
	}

	require.NoError(t, inst.upgrade(t.Context(), &Config{}, "localhost/quay:new", "9443"))

	content := string(mustReadFile(t, env.QuadletPath(quadletServiceName)))
	assert.Contains(t, content, "Exec=serve --config /data/config.yaml --hostname registry.example.com")
	assert.Contains(t, content, "Image=localhost/quay:new")
	assert.Contains(t, content, "PublishPort=9443:8443")
}

func TestResolveHostnameForFreshInstall(t *testing.T) {
	tests := []struct {
		name      string
		detected  string
		detectErr error
		want      string
		wantErr   string
	}{
		{
			name:     "fully qualified hostname",
			detected: "registry.example.com\n",
			want:     "registry.example.com",
		},
		{
			name:     "empty hostname",
			detected: "  \n",
			wantErr:  "system hostname is empty",
		},
		{
			name:     "single-label hostname",
			detected: "registry",
			wantErr:  "is not a fully qualified domain name",
		},
		{
			name:     "IP address",
			detected: "192.0.2.10",
			wantErr:  "is not a fully qualified domain name",
		},
		{
			name:     "invalid hostname",
			detected: "registry_.example.com",
			wantErr:  "invalid system hostname",
		},
		{
			name:      "detection failure",
			detectErr: errors.New("host identity unavailable"),
			wantErr:   "auto-detect system hostname: host identity unavailable",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			inst := &Installer{hostname: func(context.Context) (string, error) {
				return tt.detected, tt.detectErr
			}}

			got, err := inst.resolveHostname(t.Context(), "", false)
			if tt.wantErr != "" {
				require.ErrorContains(t, err, tt.wantErr)
				return
			}
			require.NoError(t, err)
			assert.Equal(t, tt.want, got)
		})
	}
}

func TestResolveHostnamePreservesExplicitSingleLabel(t *testing.T) {
	detected := false
	inst := &Installer{hostname: func(context.Context) (string, error) {
		detected = true
		return "ignored.example.com", nil
	}}

	got, err := inst.resolveHostname(t.Context(), "registry", false)

	require.NoError(t, err)
	assert.Equal(t, "registry", got)
	assert.False(t, detected)
}

func TestResolveHostnameHonorsCancellationBeforeDetection(t *testing.T) {
	ctx, cancel := context.WithCancel(t.Context())
	cancel()
	detected := false
	inst := &Installer{hostname: func(context.Context) (string, error) {
		detected = true
		return "registry.example.com", nil
	}}

	_, err := inst.resolveHostname(ctx, "", false)

	require.ErrorIs(t, err, context.Canceled)
	assert.False(t, detected)
}

func TestResolveHostnamePreservesUpgradeHostname(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	quadlet := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, quadlet.Install(quadletServiceName, &system.QuadletSpec{
		Image:    "localhost/quay:old",
		DataDir:  "/var/lib/quay",
		Hostname: "installed.example.com",
		Port:     "8443",
	}))
	detected := false
	inst := &Installer{
		quadlet: quadlet,
		hostname: func(context.Context) (string, error) {
			detected = true
			return "machine.example.com", nil
		},
	}

	got, err := inst.resolveHostname(t.Context(), "", true)

	require.NoError(t, err)
	assert.Equal(t, "installed.example.com", got)
	assert.False(t, detected)
}

func TestRunStopsBeforeInstallationWhenHostnameDetectionFails(t *testing.T) {
	root := t.TempDir()
	dataDir := filepath.Join(root, "registry-data")
	env := &system.Env{Mode: system.UserMode, HomeDir: filepath.Join(root, "home")}
	inst := &Installer{
		quadlet: system.NewQuadletManager(system.OSFS{}, env),
		hostname: func(context.Context) (string, error) {
			return "", errors.New("host identity unavailable")
		},
	}

	err := inst.Run(t.Context(), &Config{DataDir: dataDir})

	require.ErrorContains(t, err, "resolve hostname: auto-detect system hostname: host identity unavailable")
	_, statErr := os.Stat(dataDir)
	assert.ErrorIs(t, statErr, os.ErrNotExist)
}

func TestInitializeValidatesBeforeFilesystemChanges(t *testing.T) {
	root := t.TempDir()
	tests := []struct {
		name     string
		username string
		password string
		wantErr  string
	}{
		{name: "username", username: "bad user", password: "valid-password", wantErr: "invalid username"},
		{name: "password length", username: "admin", password: string(make([]byte, 73)), wantErr: "must not exceed 72 bytes"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			dataDir := filepath.Join(root, test.name)
			err := Initialize(t.Context(), &Config{
				DataDir:         dataDir,
				InitUser:        test.username,
				InitPassword:    test.password,
				InitPasswordSet: true,
			})
			require.ErrorContains(t, err, test.wantErr)
			_, statErr := os.Stat(dataDir)
			assert.ErrorIs(t, statErr, os.ErrNotExist)
		})
	}
}

func TestInitializeCredentialDestinationSafety(t *testing.T) {
	t.Run("rejects symlink", func(t *testing.T) {
		dataDir := initializedEmptyDataDir(t)
		authDir := filepath.Join(dataDir, "auth")
		require.NoError(t, os.Mkdir(authDir, 0o700))
		target := filepath.Join(t.TempDir(), "target")
		require.NoError(t, os.WriteFile(target, []byte("unchanged"), 0o600))
		require.NoError(t, os.Symlink(target, filepath.Join(authDir, "admin-password")))

		err := Initialize(t.Context(), &Config{
			DataDir: dataDir, InitUser: "admin",
			InitPassword: "replacement-password", InitPasswordSet: true,
		})
		require.ErrorContains(t, err, "is not a regular file")
		assert.Equal(t, []byte("unchanged"), mustReadFile(t, target))
	})

	t.Run("rejects unsafe existing generated credential", func(t *testing.T) {
		dataDir := initializedEmptyDataDir(t)
		authDir := filepath.Join(dataDir, "auth")
		require.NoError(t, os.Mkdir(authDir, 0o700))
		passwordPath := filepath.Join(authDir, "admin-password")
		require.NoError(t, os.WriteFile(passwordPath, []byte("existing-password"), 0o644))

		err := Initialize(t.Context(), &Config{DataDir: dataDir, InitUser: "admin"})
		require.ErrorContains(t, err, "unsafe permissions")
		assert.Equal(t, []byte("existing-password"), mustReadFile(t, passwordPath))
	})

	t.Run("atomically replaces failed bootstrap password", func(t *testing.T) {
		dataDir := initializedEmptyDataDir(t)
		authDir := filepath.Join(dataDir, "auth")
		require.NoError(t, os.Mkdir(authDir, 0o750))
		passwordPath := filepath.Join(authDir, "admin-password")
		require.NoError(t, os.WriteFile(passwordPath, []byte(string(make([]byte, 73))), 0o644))

		require.NoError(t, Initialize(t.Context(), &Config{
			DataDir: dataDir, InitUser: "admin",
			InitPassword: "corrected-password", InitPasswordSet: true,
		}))
		assert.Equal(t, []byte("corrected-password"), mustReadFile(t, passwordPath))
		info, err := os.Stat(passwordPath)
		require.NoError(t, err)
		assert.Equal(t, os.FileMode(0o600), info.Mode().Perm())
	})
}

func TestInitializeUsesMountedConfigDatabase(t *testing.T) {
	dataDir := t.TempDir()
	configPath := filepath.Join(dataDir, "config.yaml")
	require.NoError(t, os.WriteFile(configPath, []byte(`
SERVER_HOSTNAME: registry.example.com
PREFERRED_URL_SCHEME: https
DB_URI: sqlite:////data/custom.db
DISTRIBUTED_STORAGE_CONFIG:
  default:
    - LocalStorage
    - storage_path: /data/storage
SUPER_USERS:
  - custom-admin
`), 0o600))

	require.NoError(t, Initialize(t.Context(), &Config{
		DataDir:         dataDir,
		ConfigPath:      "/data/config.yaml",
		InitUser:        "custom-admin",
		InitPassword:    "chosen-password",
		InitPasswordSet: true,
	}))
	_, err := os.Stat(filepath.Join(dataDir, "custom.db"))
	require.NoError(t, err)
	_, err = os.Stat(filepath.Join(dataDir, "quay.db"))
	assert.ErrorIs(t, err, os.ErrNotExist)
}

func TestInitializeRequiresConfiguredSuperuserForExplicitConfig(t *testing.T) {
	dataDir := t.TempDir()
	configPath := filepath.Join(dataDir, "config.yaml")
	require.NoError(t, os.WriteFile(configPath, []byte(`
SERVER_HOSTNAME: registry.example.com
PREFERRED_URL_SCHEME: https
DB_URI: sqlite:////data/quay.db
DISTRIBUTED_STORAGE_CONFIG:
  default:
    - LocalStorage
    - storage_path: /data/storage
SUPER_USERS:
  - configured-admin
`), 0o600))

	err := Initialize(t.Context(), &Config{
		DataDir:         dataDir,
		ConfigPath:      "/data/config.yaml",
		InitUser:        "different-admin",
		InitPassword:    "chosen-password",
		InitPasswordSet: true,
	})
	require.ErrorContains(t, err, `initial username "different-admin" is not listed in SUPER_USERS`)
	_, statErr := os.Stat(filepath.Join(dataDir, "auth", "admin-password"))
	assert.ErrorIs(t, statErr, os.ErrNotExist)
}

func initializedEmptyDataDir(t *testing.T) string {
	t.Helper()
	dataDir := t.TempDir()
	db, err := dbcore.Setup(t.Context(), filepath.Join(dataDir, "quay.db"))
	require.NoError(t, err)
	require.NoError(t, db.Close())
	return dataDir
}

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

func TestValidateUpgradePortChangeRejectsConfigBackedInstall(t *testing.T) {
	env := &system.Env{Mode: system.UserMode, HomeDir: t.TempDir()}
	quadlet := system.NewQuadletManager(system.OSFS{}, env)
	require.NoError(t, quadlet.Install(quadletServiceName, &system.QuadletSpec{
		Image: "localhost/quay:old", DataDir: "/var/lib/quay", Hostname: "registry.example.com",
		Port: "8443", ConfigPath: "/data/config.yaml",
	}))
	inst := &Installer{quadlet: quadlet}

	err := inst.validateUpgradePortChange("9443", "9443", true)

	require.ErrorContains(t, err, "cannot change port from 8443 to 9443")
	assert.ErrorContains(t, err, "update SERVER_HOSTNAME in /data/config.yaml first")
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
	require.NoError(t, os.WriteFile(quadletPath, []byte("[Container]\nImage=localhost/quay:test\nExec=serve --data-dir /data --hostname registry.example.com\n"), 0o600))

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

func (r *recordingServiceManager) DisableLinger(context.Context) error {
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
