package migrate

import (
	"context"
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/installer"
	postgrescopy "github.com/quay/quay/internal/migrate/postgres"
)

const partialDatabaseName = "quay.db.partial"

func (m *Migrator) runPostgresMigration(ctx context.Context) (retErr error) {
	if err := m.validatePostgresFlags(); err != nil {
		return err
	}
	if err := m.validatePostgresBeforeStop(ctx); err != nil {
		return fmt.Errorf("validate: %w", err)
	}
	retrySafe := true
	defer func() {
		if retErr == nil {
			return
		}
		rollbackCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if cleanupErr := m.removePostgresMigrationArtifacts(retrySafe); cleanupErr != nil {
			retErr = errors.Join(retErr, fmt.Errorf("remove failed migration artifacts: %w", cleanupErr))
		}
		if rollbackErr := m.rollbackPostgresSource(rollbackCtx); rollbackErr != nil {
			retErr = errors.Join(retErr, fmt.Errorf("rollback old OMR: %w", rollbackErr))
		}
	}()
	if err := m.stopPostgresApp(ctx); err != nil {
		return fmt.Errorf("stop old OMR app: %w", err)
	}

	if err := os.MkdirAll(m.DataDir, 0o750); err != nil {
		return fmt.Errorf("create target directory: %w", err)
	}
	if err := os.WriteFile(filepath.Join(m.DataDir, markerFile), []byte("migration in progress\n"), 0o600); err != nil {
		return fmt.Errorf("write migration marker: %w", err)
	}
	if err := m.runPostgresCopyInNamespace(ctx); err != nil {
		return fmt.Errorf("convert PostgreSQL source: %w", err)
	}
	m.Source.DBPath = m.postgresPartialDBPath()
	if err := m.validateSourceDatabase(ctx); err != nil {
		return fmt.Errorf("validate converted source: %w", err)
	}
	// Once broad target publication begins, retain the marker so a later failure
	// remains fail-closed rather than being mistaken for a clean retry.
	retrySafe = false
	if err := m.copyData(ctx); err != nil {
		return fmt.Errorf("copy: %w", err)
	}
	if err := m.upgradeSchema(ctx); err != nil {
		return fmt.Errorf("schema upgrade: %w", err)
	}
	if err := m.stopPostgresRemainingServices(ctx); err != nil {
		return fmt.Errorf("stop old OMR at cutover: %w", err)
	}
	if err := m.install(ctx); err != nil {
		return fmt.Errorf("install: %w", err)
	}
	return nil
}

func (m *Migrator) validatePostgresFlags() error {
	var unsupported []string
	if m.DryRun {
		unsupported = append(unsupported, "-dry-run")
	}
	if m.SkipInstall {
		unsupported = append(unsupported, "-skip-install")
	}
	if m.Cleanup {
		unsupported = append(unsupported, "-cleanup")
	}
	if len(unsupported) > 0 {
		return fmt.Errorf("PostgreSQL migration does not support %s", strings.Join(unsupported, ", "))
	}
	return nil
}

func (m *Migrator) validatePostgresBeforeStop(ctx context.Context) error {
	hasInstallation, err := m.hasTargetInstallation()
	if err != nil {
		return fmt.Errorf("check target installation: %w", err)
	}
	if hasInstallation {
		return fmt.Errorf("an existing target Quay installation must be removed before PostgreSQL migration")
	}
	if err := validatePostgresTargetDir(m.DataDir); err != nil {
		return err
	}
	if _, err := m.validateSourceAuthConfig(); err != nil {
		return fmt.Errorf("source authentication preflight: %w", err)
	}
	sourceCfg, err := config.Load(filepath.Join(m.Source.ConfigDir, runtimeConfigFile))
	if err != nil {
		return fmt.Errorf("load source config for registry JWT key capture: %w", err)
	}
	key, kid, err := loadRegistryJWTSigningKey(ctx, m.Source.ConfigDir, sourceCfg, m.Runner)
	if err != nil {
		return fmt.Errorf("registry JWT key capture: %w", err)
	}
	m.sourceRegistryJWTKey = key
	m.sourceRegistryJWTKID = kid
	return m.validateCommonInputs()
}

func validatePostgresTargetDir(path string) error {
	entries, err := os.ReadDir(path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("read target directory %s: %w", path, err)
	}
	if len(entries) > 0 {
		for _, e := range entries {
			if e.Name() == markerFile {
				return fmt.Errorf("target directory %s is not clean (found %s): PostgreSQL migration does not support resuming a previous migration — specify a clean directory or remove existing files", path, markerFile)
			}
		}
		return fmt.Errorf("target directory %s is not clean (found %d existing file(s)) — specify a clean directory or remove existing files before PostgreSQL migration", path, len(entries))
	}
	return nil
}

func (m *Migrator) hasTargetInstallation() (bool, error) {
	if m.checkTargetInstallation != nil {
		return m.checkTargetInstallation()
	}
	inst, err := installer.New(m.Out)
	if err != nil {
		return false, err
	}
	return inst.HasInstallation(), nil
}

func (m *Migrator) inPostgresNetworkNamespace() (bool, error) {
	current, err := os.Stat("/proc/self/ns/net")
	if err != nil {
		return false, err
	}
	target, err := os.Stat(m.Source.PodSandboxKey)
	if err != nil {
		return false, err
	}
	return os.SameFile(current, target), nil
}

func (m *Migrator) runPostgresCopyInNamespace(ctx context.Context) error {
	if m.Runner == nil {
		return fmt.Errorf("no command runner for PostgreSQL conversion")
	}
	executable, err := os.Executable()
	if err != nil {
		return fmt.Errorf("locate current executable: %w", err)
	}
	reexec := []string{"--net=" + m.Source.PodSandboxKey, executable, "migrate", "-data-dir=" + m.DataDir, "-source-certs=" + m.Source.ConfigDir}
	if m.Source.SystemdScope == scopeUser {
		return m.Runner.Run(ctx, "podman", append([]string{"unshare", "nsenter"}, reexec...)...)
	}
	return m.Runner.Run(ctx, "nsenter", reexec...)
}

func (m *Migrator) copyPostgresSource(ctx context.Context) (retErr error) {
	sourceCfg, err := config.Load(filepath.Join(m.Source.ConfigDir, runtimeConfigFile))
	if err != nil {
		return fmt.Errorf("load source config: %w", err)
	}
	dsn, err := postgresLoopbackURI(sourceCfg.DBURI)
	if err != nil {
		return err
	}
	pg, err := pgx.Connect(ctx, dsn)
	if err != nil {
		return postgresConnectionError(err)
	}
	defer func() { _ = pg.Close(context.Background()) }()

	targetPath := m.postgresPartialDBPath()
	if _, err := os.Stat(targetPath); err == nil {
		return fmt.Errorf("intermediate database already exists")
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("stat intermediate database: %w", err)
	}
	defer func() {
		if retErr != nil {
			_ = os.Remove(targetPath)
			_ = os.Remove(targetPath + "-wal")
			_ = os.Remove(targetPath + "-shm")
		}
	}()

	if err := createIntermediateDatabaseFile(targetPath); err != nil {
		return err
	}
	db, err := dbcore.OpenSQLite(targetPath)
	if err != nil {
		return fmt.Errorf("open intermediate database: %w", err)
	}
	defer func() { _ = db.Close() }()
	if err := dbcore.InitOMRSourceIntermediate(ctx, db); err != nil {
		return fmt.Errorf("initialize intermediate database: %w", err)
	}
	if _, err := postgrescopy.CopyPostgresToSQLite(ctx, pg, db); err != nil {
		return fmt.Errorf("copy PostgreSQL source: %w", err)
	}
	return nil
}

func postgresConnectionError(err error) error {
	if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
		return fmt.Errorf("connect to source PostgreSQL: %w", err)
	}
	var connectErr *pgconn.ConnectError
	if errors.As(err, &connectErr) {
		if cause := errors.Unwrap(connectErr); cause != nil {
			return fmt.Errorf("connect to source PostgreSQL: %w", cause)
		}
	}
	return errors.New("connect to source PostgreSQL: connection failed")
}

func createIntermediateDatabaseFile(path string) error {
	file, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600) //nolint:gosec // path is the validated migration target
	if err != nil {
		return fmt.Errorf("create intermediate database: %w", err)
	}
	if err := file.Close(); err != nil {
		return fmt.Errorf("create intermediate database: %w", err)
	}
	return nil
}

func (m *Migrator) removePostgresMigrationArtifacts(removeMarker bool) error {
	partialPath := m.postgresPartialDBPath()
	paths := []string{
		partialPath,
		partialPath + "-wal",
		partialPath + "-shm",
	}
	if removeMarker {
		paths = append(paths, filepath.Join(m.DataDir, markerFile))
	}
	var errs []error
	for _, path := range paths {
		if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
			errs = append(errs, fmt.Errorf("remove %s: %w", path, err))
		}
	}
	return errors.Join(errs...)
}

func postgresLoopbackURI(raw string) (string, error) {
	u, err := parsePostgresURI(raw)
	if err != nil {
		return "", err
	}
	if u.Port() == "" {
		u.Host = "127.0.0.1"
	} else {
		u.Host = net.JoinHostPort("127.0.0.1", u.Port())
	}
	return u.String(), nil
}

func (m *Migrator) postgresPartialDBPath() string {
	return filepath.Join(m.DataDir, partialDatabaseName)
}
