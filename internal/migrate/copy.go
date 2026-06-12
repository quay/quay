package migrate

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
)

func (m *Migrator) copyData(_ context.Context) error {
	if err := os.MkdirAll(m.DataDir, 0o750); err != nil {
		return fmt.Errorf("create target directory: %w", err)
	}

	markerPath := filepath.Join(m.DataDir, markerFile)
	if err := os.WriteFile(markerPath, []byte("migration in progress\n"), 0o600); err != nil {
		return fmt.Errorf("write marker: %w", err)
	}

	// Copy database (rename quay_sqlite.db → quay.db).
	targetDB := filepath.Join(m.DataDir, "quay.db")
	if err := copyFileIdempotent(m.Source.DBPath, targetDB); err != nil {
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
			if err := copyFileIdempotent(src, dst); err != nil {
				return fmt.Errorf("copy %s: %w", name, err)
			}
			slog.Info("copied cert", "src", src, "dst", dst)
		}
	}

	// Copy blob storage recursively.
	if m.Source.StoragePath != "" {
		targetStorage := filepath.Join(m.DataDir, "storage")
		count, totalBytes, err := copyDirRecursive(m.Source.StoragePath, targetStorage, m.Out)
		if err != nil {
			return fmt.Errorf("copy storage: %w", err)
		}
		slog.Info("copied storage", "files", count, "bytes", totalBytes)
	}

	return nil
}

// copyFileIdempotent copies src to dst, skipping if dst already exists with matching size.
func copyFileIdempotent(src, dst string) error {
	srcInfo, err := os.Stat(src)
	if err != nil {
		return fmt.Errorf("stat source: %w", err)
	}

	dstInfo, dstErr := os.Stat(dst)
	if dstErr == nil && dstInfo.Size() == srcInfo.Size() {
		return nil // already copied
	}

	in, err := os.Open(src) //nolint:gosec // path from validated source
	if err != nil {
		return err
	}
	defer func() { _ = in.Close() }()

	out, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, srcInfo.Mode()) //nolint:gosec // path from caller
	if err != nil {
		return err
	}
	defer func() { _ = out.Close() }()

	if _, err := io.Copy(out, in); err != nil {
		return err
	}
	return out.Close()
}

// copyDirRecursive copies the contents of srcDir into dstDir.
func copyDirRecursive(srcDir, dstDir string, w io.Writer) (files int, totalBytes int64, _ error) {
	err := filepath.Walk(srcDir, func(srcPath string, info os.FileInfo, err error) error {
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

		if err := copyFileIdempotent(srcPath, dstPath); err != nil {
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
