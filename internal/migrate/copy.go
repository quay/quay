package migrate

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/dal/dbcore"
)

func (m *Migrator) copyData(ctx context.Context) error {
	if err := os.MkdirAll(m.DataDir, 0o750); err != nil {
		return fmt.Errorf("create target directory: %w", err)
	}

	markerPath := filepath.Join(m.DataDir, markerFile)
	resuming := false
	if _, err := os.Stat(markerPath); err == nil {
		resuming = true
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("stat marker: %w", err)
	}
	if err := os.WriteFile(markerPath, []byte("migration in progress\n"), 0o600); err != nil {
		return fmt.Errorf("write marker: %w", err)
	}

	// Dockerfile.mirror currently runs the Go registry as root, so preserving
	// source modes is enough. If the image moves to a non-root USER, add an
	// ownership or ACL normalization step for the target data directory here.

	// Copy database (rename quay_sqlite.db → quay.db).
	if err := checkpointSQLite(ctx, m.Source.DBPath); err != nil {
		return fmt.Errorf("checkpoint source database: %w", err)
	}
	targetDB := filepath.Join(m.DataDir, "quay.db")
	if resuming {
		slog.Info("migration marker already existed, recopying database", "dst", targetDB)
	}
	if err := copyFileIdempotent(ctx, m.Source.DBPath, targetDB, resuming); err != nil {
		return fmt.Errorf("copy database: %w", err)
	}
	slog.Info("copied database", "src", m.Source.DBPath, "dst", targetDB)

	// Copy TLS certs (flatten from quay-config/ to data-dir root).
	if m.Source.ConfigDir != "" {
		for _, name := range []string{"ssl.cert", "ssl.key"} {
			src := filepath.Join(m.Source.ConfigDir, name)
			dst := filepath.Join(m.DataDir, name)
			if _, err := os.Stat(src); err != nil {
				slog.Warn("cert file not found, skipping", "path", src)
				continue
			}
			if err := copyFileIdempotent(ctx, src, dst, false); err != nil {
				return fmt.Errorf("copy %s: %w", name, err)
			}
			slog.Info("copied cert", "src", src, "dst", dst)
		}
	}

	// Copy blob storage recursively.
	if m.Source.StoragePath != "" {
		targetStorage := filepath.Join(m.DataDir, "storage")
		count, totalBytes, err := copyDirRecursive(ctx, m.Source.StoragePath, targetStorage, m.Out)
		if err != nil {
			return fmt.Errorf("copy storage: %w", err)
		}
		slog.Info("copied storage", "files", count, "bytes", totalBytes)
	}

	return nil
}

func checkpointSQLite(ctx context.Context, dbPath string) (retErr error) {
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		return fmt.Errorf("open database: %w", err)
	}
	defer func() {
		if cerr := db.Close(); cerr != nil && retErr == nil {
			retErr = fmt.Errorf("close database: %w", cerr)
		}
	}()

	if _, err := db.ExecContext(ctx, "PRAGMA wal_checkpoint(TRUNCATE)"); err != nil {
		return fmt.Errorf("wal checkpoint: %w", err)
	}
	return nil
}

// copyFileIdempotent copies src to dst, skipping if dst already exists with matching size.
func copyFileIdempotent(ctx context.Context, src, dst string, force bool) (retErr error) {
	if err := ctx.Err(); err != nil {
		return err
	}

	srcInfo, err := os.Stat(src)
	if err != nil {
		return fmt.Errorf("stat source: %w", err)
	}

	dstInfo, dstErr := os.Stat(dst)
	if !force && dstErr == nil && dstInfo.Size() == srcInfo.Size() {
		return nil // already copied
	}

	if err := ctx.Err(); err != nil {
		return err
	}

	in, err := os.Open(src) //nolint:gosec // path from validated source
	if err != nil {
		return err
	}
	defer func() {
		if cerr := in.Close(); cerr != nil && retErr == nil {
			retErr = fmt.Errorf("close source: %w", cerr)
		}
	}()

	out, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, srcInfo.Mode()) //nolint:gosec // path from caller
	if err != nil {
		return err
	}

	if _, err := io.Copy(out, in); err != nil {
		if cerr := out.Close(); cerr != nil {
			return errors.Join(
				fmt.Errorf("copy file: %w", err),
				fmt.Errorf("close destination: %w", cerr),
			)
		}
		return err
	}
	if err := out.Close(); err != nil {
		return fmt.Errorf("close destination: %w", err)
	}
	return nil
}

// copyDirRecursive copies the contents of srcDir into dstDir.
func copyDirRecursive(ctx context.Context, srcDir, dstDir string, w io.Writer) (files int, totalBytes int64, _ error) {
	err := filepath.Walk(srcDir, func(srcPath string, info os.FileInfo, err error) error {
		if err := ctx.Err(); err != nil {
			return err
		}
		if err != nil {
			return err
		}

		relPath, err := filepath.Rel(srcDir, srcPath)
		if err != nil {
			return err
		}
		dstPath := filepath.Join(dstDir, relPath)

		if info.IsDir() {
			return os.MkdirAll(dstPath, info.Mode())
		}

		if err := copyFileIdempotent(ctx, srcPath, dstPath, false); err != nil {
			return fmt.Errorf("copy %s: %w", relPath, err)
		}

		files++
		totalBytes += info.Size()

		if files%1000 == 0 {
			fmt.Fprintf(w, "  copied %d files (%d MB)...\n", files, totalBytes/(1024*1024))
		}

		return nil
	})

	return files, totalBytes, err
}

func removeMarker(dataDir string) {
	_ = os.Remove(filepath.Join(dataDir, markerFile))
}
