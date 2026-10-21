// Package migrate implements the OMR-to-Go-binary migration workflow.
package migrate

import (
	"context"
	"crypto/rsa"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/installer"
	"github.com/quay/quay/internal/system"
)

const (
	scopeSystem     = "system"
	scopeUser       = "user"
	systemdUserFlag = "--user"

	databaseSQLite   = "sqlite"
	databasePostgres = "postgres"

	// failAtEnv names a phase at which the migration fails on purpose. It
	// exists for tests that exercise rollback against a real OMR.
	failAtEnv = "QUAY_MIGRATE_FAIL_AT"
)

// OMRSource describes a detected OMR v2.0.x installation.
type OMRSource struct {
	DatabaseKind string
	ConfigDir    string // path to quay-config/ (config.yaml, ssl.cert, ssl.key)
	DBPath       string // path to quay_sqlite.db; empty for PostgreSQL
	StoragePath  string // path to blob storage root
	Hostname     string // from old config.yaml SERVER_HOSTNAME (bare, no port)
	Port         string // from old config.yaml SERVER_HOSTNAME (empty = default 8443)
	RootCADir    string // path to quay-rootCA/ directory containing rootCA.pem

	ImageArchive string // container image tar path
	Image        string // container image ref (alternative)

	SystemdScope  string   // "system" or "user"
	PodSandboxKey string   // PostgreSQL only: quay-pod network namespace path
	UnitFiles     []string // old systemd unit file paths
	VolumeNames   []string // podman volume names
	Method        string   // "systemd", "podman-volume", or "defaults"
}

// checkpointFunc is the signature for the WAL checkpoint operation.
type checkpointFunc func(ctx context.Context, dbPath string) error

// Migrator orchestrates the OMR-to-Go-binary migration phases.
type Migrator struct {
	Source OMRSource

	DataDir      string
	Hostname     string
	Image        string
	ImageArchive string

	SourceRoot    string
	SourceDB      string
	SourceStorage string
	SourceCerts   string

	DryRun      bool
	Cleanup     bool
	SkipInstall bool

	Out        io.Writer
	Runner     system.CommandRunner
	Checkpoint checkpointFunc

	sourceRegistryJWTKey    *rsa.PrivateKey
	sourceRegistryJWTKID    string
	checkTargetInstallation func() (bool, error)
	removeTargetInstall     func(context.Context) error
	runInstall              func(context.Context, *installer.Config) error
	sourceStopped           bool
	ownsTargetInstall       bool
	persistedConfigFiles    []string
}

// Run executes the migration phases in order.
func (m *Migrator) Run(ctx context.Context) error {
	if m.Out == nil {
		m.Out = os.Stderr
	}

	if err := m.detectAndOverride(ctx); err != nil {
		return err
	}

	if m.Source.DatabaseKind == databasePostgres {
		inside, err := m.inPostgresNetworkNamespace()
		if err != nil {
			return fmt.Errorf("detect current network namespace: %w", err)
		}
		if inside {
			return m.copyPostgresSource(ctx)
		}
		return m.runPostgresMigration(ctx)
	}
	return m.runSQLiteMigration(ctx)
}

func (m *Migrator) runSQLiteMigration(ctx context.Context) error {
	if m.DryRun {
		if err := m.validate(ctx); err != nil {
			return errors.Join(fmt.Errorf("validate: %w", err), m.removePersistedConfigMaterial())
		}
		m.printPlan()
		return m.removePersistedConfigMaterial()
	}

	if err := m.refuseResumeOverInstall(); err != nil {
		return err
	}

	// If cleanup-only (target dir already populated from a previous migration),
	// skip the migration phases and just clean up the old OMR.
	if m.Cleanup && targetDirPopulated(m.DataDir) {
		if err := m.cleanup(ctx); err != nil {
			return fmt.Errorf("cleanup: %w", err)
		}
		slog.Info("cleanup complete")
		return nil
	}

	if err := m.migrateAndInstall(ctx); err != nil {
		return err
	}

	if m.Cleanup {
		if err := m.cleanup(ctx); err != nil {
			return fmt.Errorf("cleanup: %w", err)
		}
	}

	slog.Info("migration complete")
	return nil
}

// migrateAndInstall restarts the old OMR when a step fails after it was
// stopped, and removes this run's recovered key files when a step fails
// before the stop. The failed target keeps its marker, so a rerun resumes the
// copy.
func (m *Migrator) migrateAndInstall(ctx context.Context) (retErr error) {
	defer func() {
		if retErr == nil {
			return
		}
		if !m.sourceStopped {
			// Nothing to restart, but key material validation recovered from
			// the running container must not stay in the source config dir.
			if err := m.removePersistedConfigMaterial(); err != nil {
				retErr = errors.Join(retErr, err)
			}
			return
		}
		retErr = withSourceRollback(retErr, m.rollbackSQLiteSource(context.Background()))
	}()
	if err := m.migrateData(ctx); err != nil {
		return err
	}
	if m.SkipInstall {
		// The copy is complete, so a later -cleanup must not resume it over
		// a database the user may have installed by hand.
		if err := removeMarker(m.DataDir); err != nil {
			return fmt.Errorf("remove migration marker: %w", err)
		}
		return nil
	}
	if err := m.install(ctx); err != nil {
		return fmt.Errorf("install: %w", err)
	}
	return nil
}

// targetDirPopulated reports a finished migration. A marker means the target
// is an interrupted copy, which must be resumed rather than cleaned up after.
func targetDirPopulated(dir string) bool {
	if _, err := os.Stat(filepath.Join(dir, markerFile)); err == nil {
		return false
	}
	_, err := os.Stat(filepath.Join(dir, "quay.db"))
	return err == nil
}

// refuseResumeOverInstall keeps a rerun from recopying over a finished
// migration: install removes the marker only after the new registry is
// running, and that removal can be interrupted or fail.
func (m *Migrator) refuseResumeOverInstall() error {
	markerPath := filepath.Join(m.DataDir, markerFile)
	if _, err := os.Stat(markerPath); errors.Is(err, os.ErrNotExist) {
		return nil
	} else if err != nil {
		return fmt.Errorf("check migration marker: %w", err)
	}
	installed, err := m.hasTargetInstallation()
	if err != nil {
		return fmt.Errorf("check target installation: %w", err)
	}
	if !installed {
		return nil
	}
	return fmt.Errorf("target directory %s has a migration marker but a Quay installation already exists, refusing to resume and recopy over it: "+
		"if that installation serves %s and is healthy, the migration finished, so remove %s and rerun with -cleanup; "+
		"otherwise run 'mirror-registry uninstall' and rerun the migration", m.DataDir, m.DataDir, markerPath)
}

func failAt(phase string) error {
	if os.Getenv(failAtEnv) == phase {
		return fmt.Errorf("injected failure at %s", phase)
	}
	return nil
}

func (m *Migrator) migrateData(ctx context.Context) error {
	if err := m.validate(ctx); err != nil {
		return fmt.Errorf("validate: %w", err)
	}
	if err := m.stopSourceServices(ctx); err != nil {
		return fmt.Errorf("stop old OMR: %w", err)
	}
	return m.copyAndUpgrade(ctx)
}

func (m *Migrator) copyAndUpgrade(ctx context.Context) error {
	if err := m.copyData(ctx); err != nil {
		return fmt.Errorf("copy: %w", err)
	}
	if err := failAt("after-copy"); err != nil {
		return err
	}
	if err := m.upgradeSchema(ctx); err != nil {
		return fmt.Errorf("schema upgrade: %w", err)
	}
	return failAt("after-schema")
}

func (m *Migrator) detectAndOverride(ctx context.Context) error {
	m.applyOverrides()

	if m.Source.DBPath == "" {
		src, err := m.detect(ctx)
		if err != nil {
			return fmt.Errorf("detect: %w", err)
		}
		m.Source = src
		m.applyOverrides()
	} else if m.Source.Method == "" {
		m.Source.Method = "manual"
		m.Source = m.withImageArchive(&m.Source)
	}
	return nil
}

func (m *Migrator) applyOverrides() {
	if m.Hostname != "" {
		m.Source.Hostname = m.Hostname
	}
	if m.SourceDB != "" {
		m.Source.DBPath = m.SourceDB
	}
	if m.SourceStorage != "" {
		m.Source.StoragePath = m.SourceStorage
	}
	if m.SourceCerts != "" {
		m.Source.ConfigDir = m.SourceCerts
	}
	if m.ImageArchive != "" {
		m.Source.ImageArchive = m.ImageArchive
	}
	if m.Image != "" {
		m.Source.Image = m.Image
	}
}

func (m *Migrator) printPlan() {
	fmt.Fprintf(m.Out, "Detected OMR installation (via %s):\n", m.Source.Method)
	fmt.Fprintf(m.Out, "  Config:   %s\n", m.Source.ConfigDir)
	fmt.Fprintf(m.Out, "  Database: %s\n", m.Source.DBPath)
	fmt.Fprintf(m.Out, "  Storage:  %s\n", m.Source.StoragePath)
	if m.Source.Port != "" {
		fmt.Fprintf(m.Out, "  Hostname: %s (port %s)\n", m.Source.Hostname, m.Source.Port)
	} else {
		fmt.Fprintf(m.Out, "  Hostname: %s\n", m.Source.Hostname)
	}
	if m.Source.RootCADir != "" {
		fmt.Fprintf(m.Out, "  Root CA:  %s\n", m.Source.RootCADir)
	}
	if len(m.Source.UnitFiles) > 0 {
		fmt.Fprintf(m.Out, "  Services: %v (%s scope)\n", m.Source.UnitFiles, m.Source.SystemdScope)
	}
	if len(m.Source.VolumeNames) > 0 {
		fmt.Fprintf(m.Out, "  Volumes:  %v\n", m.Source.VolumeNames)
	}
	if m.Source.ImageArchive != "" {
		fmt.Fprintf(m.Out, "  Image:    %s (auto-detected)\n", m.Source.ImageArchive)
	}
	fmt.Fprintf(m.Out, "\nTarget: %s/\n", m.DataDir)
}
