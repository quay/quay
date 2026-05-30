package system

import "os"

// FileSystem abstracts filesystem operations for testability.
type FileSystem interface {
	ReadFile(path string) ([]byte, error)
	WriteFile(path string, data []byte, perm os.FileMode) error
	MkdirAll(path string, perm os.FileMode) error
	Stat(path string) (os.FileInfo, error)
}

// OSFS implements FileSystem using the real filesystem.
type OSFS struct{}

func (OSFS) ReadFile(path string) ([]byte, error)                        { return os.ReadFile(path) } //nolint:gosec // paths from known locations
func (OSFS) WriteFile(path string, data []byte, perm os.FileMode) error  { return os.WriteFile(path, data, perm) } //nolint:gosec // paths from known locations
func (OSFS) MkdirAll(path string, perm os.FileMode) error                { return os.MkdirAll(path, perm) }
func (OSFS) Stat(path string) (os.FileInfo, error)                       { return os.Stat(path) }
