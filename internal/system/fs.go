package system

import "os"

// FileSystem abstracts filesystem operations for testability.
type FileSystem interface {
	ReadFile(path string) ([]byte, error)
	WriteFile(path string, data []byte, perm os.FileMode) error
	MkdirAll(path string, perm os.FileMode) error
	MkdirTemp(dir, pattern string) (string, error)
	Stat(path string) (os.FileInfo, error)
	Lstat(path string) (os.FileInfo, error)
	Chmod(path string, mode os.FileMode) error
	Link(oldPath, newPath string) error
	Rename(oldPath, newPath string) error
	Remove(path string) error
	RemoveAll(path string) error
}

// OSFS implements FileSystem using the real filesystem.
type OSFS struct{}

var _ FileSystem = OSFS{}

// ReadFile delegates to os.ReadFile.
func (OSFS) ReadFile(path string) ([]byte, error) { return os.ReadFile(path) } //nolint:gosec // paths from known locations

// WriteFile delegates to os.WriteFile.
func (OSFS) WriteFile(path string, data []byte, perm os.FileMode) error {
	return os.WriteFile(path, data, perm)
} //nolint:gosec // paths from known locations

// MkdirAll delegates to os.MkdirAll.
func (OSFS) MkdirAll(path string, perm os.FileMode) error { return os.MkdirAll(path, perm) }

// MkdirTemp delegates to os.MkdirTemp.
func (OSFS) MkdirTemp(dir, pattern string) (string, error) { return os.MkdirTemp(dir, pattern) }

// Stat delegates to os.Stat.
func (OSFS) Stat(path string) (os.FileInfo, error) { return os.Stat(path) }

// Lstat delegates to os.Lstat.
func (OSFS) Lstat(path string) (os.FileInfo, error) { return os.Lstat(path) }

// Chmod delegates to os.Chmod.
func (OSFS) Chmod(path string, mode os.FileMode) error { return os.Chmod(path, mode) }

// Link delegates to os.Link.
func (OSFS) Link(oldPath, newPath string) error { return os.Link(oldPath, newPath) }

// Rename delegates to os.Rename.
func (OSFS) Rename(oldPath, newPath string) error { return os.Rename(oldPath, newPath) }

// Remove delegates to os.Remove.
func (OSFS) Remove(path string) error { return os.Remove(path) }

// RemoveAll delegates to os.RemoveAll.
func (OSFS) RemoveAll(path string) error { return os.RemoveAll(path) } //nolint:gosec // paths from known locations
