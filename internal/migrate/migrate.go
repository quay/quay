// Package migrate implements the OMR-to-Go-binary migration workflow.
package migrate

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/system"
)

const scopeUser = "user"

// OMRSource describes a detected OMR v1.4.x installation.
type OMRSource struct {
	ConfigDir   string // path to quay-config/ (config.yaml, ssl.cert, ssl.key)
	DBPath      string // path to quay_sqlite.db
	StoragePath string // path to blob storage root
	Hostname    string // from old config.yaml SERVER_HOSTNAME

	ImageArchive string // container image tar path
	Image        string // container image ref (alternative)

	SystemdScope string   // "system" or "user"
	UnitFiles    []string // old systemd unit file paths
	VolumeNames  []string // podman volume names
	Method       string   // "systemd", "podman-volume", or "defaults"
}

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
	SkipVerify  bool
	SkipInstall bool

	Out    io.Writer
	Runner system.CommandRunner
}

// Run executes the migration phases in order.
func (m *Migrator) Run(ctx context.Context) error {
	if m.Out == nil {
		m.Out = os.Stderr
	}

	if err := m.detectAndOverride(ctx); err != nil {
		return err
	}

	if m.DryRun {
		m.printPlan()
		return nil
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

	if err := m.migrateData(ctx); err != nil {
		return err
	}

	if !m.SkipInstall {
		if err := m.install(ctx); err != nil {
			return fmt.Errorf("install: %w", err)
		}
	}

	if !m.SkipVerify && !m.SkipInstall {
		if err := m.verify(ctx); err != nil {
			return fmt.Errorf("verify: %w", err)
		}
	}

	if m.Cleanup {
		if err := m.cleanup(ctx); err != nil {
			return fmt.Errorf("cleanup: %w", err)
		}
	}

	slog.Info("migration complete")
	return nil
}

func targetDirPopulated(dir string) bool {
	_, err := os.Stat(filepath.Join(dir, "quay.db"))
	return err == nil
}

func (m *Migrator) migrateData(ctx context.Context) error {
	if err := m.validate(ctx); err != nil {
		return fmt.Errorf("validate: %w", err)
	}
	if err := m.stopOldOMR(ctx); err != nil {
		return fmt.Errorf("stop old OMR: %w", err)
	}
	if err := m.copyData(ctx); err != nil {
		return fmt.Errorf("copy: %w", err)
	}
	if err := m.convertStorage(ctx); err != nil {
		return fmt.Errorf("convert storage: %w", err)
	}
	if err := m.upgradeSchema(ctx); err != nil {
		return fmt.Errorf("schema upgrade: %w", err)
	}
	return nil
}

func (m *Migrator) detectAndOverride(ctx context.Context) error {
	if m.Source.DBPath == "" {
		src, err := m.detect(ctx)
		if err != nil {
			return fmt.Errorf("detect: %w", err)
		}
		m.Source = src
	}
	m.applyOverrides()
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
	fmt.Fprintf(m.Out, "  Hostname: %s\n", m.Source.Hostname)
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
