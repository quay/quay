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
	defer func() {
		if retErr == nil {
			return
		}
		rollbackCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
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
	inst, err := installer.New(m.Out)
	if err != nil {
		return fmt.Errorf("check target installation: %w", err)
	}
	if inst.HasInstallation() {
		return fmt.Errorf("an existing target Quay installation must be removed before PostgreSQL migration")
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
	if err := m.validateCommonInputs(); err != nil {
		return err
	}
	if _, err := os.Stat(filepath.Join(m.DataDir, markerFile)); err == nil {
		return fmt.Errorf("PostgreSQL migration does not support resuming a previous migration")
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("stat migration marker: %w", err)
	}
	return nil
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
		return errors.New("connect to source PostgreSQL: connection failed")
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

	db, err := dbcore.OpenSQLite(targetPath)
	if err != nil {
		return fmt.Errorf("open intermediate database: %w", err)
	}
	defer func() { _ = db.Close() }()
	if err := os.Chmod(targetPath, 0o600); err != nil {
		return fmt.Errorf("secure intermediate database: %w", err)
	}
	if err := dbcore.InitOMRSourceIntermediate(ctx, db); err != nil {
		return fmt.Errorf("initialize intermediate database: %w", err)
	}
	if _, err := postgrescopy.CopyPostgresToSQLite(ctx, pg, db); err != nil {
		return fmt.Errorf("copy PostgreSQL source: %w", err)
	}
	return nil
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
