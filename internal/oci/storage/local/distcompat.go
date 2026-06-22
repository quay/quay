package local

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strings"

	storagedriver "github.com/distribution/distribution/v3/registry/storage/driver"
	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage"
)

// DistDriver implements distribution's storagedriver.StorageDriver by routing
// calls to two backends based on path classification:
//   - Blob + Upload paths → oci.BlobStore
//   - Metadata paths → oci.MetadataStore (SQLite)
type DistDriver struct {
	blobs oci.BlobStore
	meta  oci.MetadataStore
}

// NewDistDriver creates a DistDriver that routes distribution storage calls.
func NewDistDriver(blobs oci.BlobStore, meta oci.MetadataStore) *DistDriver {
	return &DistDriver{blobs: blobs, meta: meta}
}

// Name returns the driver identifier registered with distribution's factory.
func (d *DistDriver) Name() string { return "quay" }

// GetContent reads small objects. Blobs are fetched by digest from the
// BlobStore, upload state from the upload directory, and metadata links
// (tags, layers, manifest revisions) from SQLite.
func (d *DistDriver) GetContent(ctx context.Context, path string) ([]byte, error) {
	switch classify(path) {
	case pathBlob:
		dgst, err := digestFromBlobPath(path)
		if err != nil {
			return nil, err
		}
		data, err := d.blobs.GetContent(ctx, dgst)
		if errors.Is(err, storage.ErrNotExist) {
			return nil, storagedriver.PathNotFoundError{Path: path}
		}
		return data, err

	case pathUpload:
		id := uploadIDFromPath(path)
		key := uploadStateKey(path)
		if key == "" {
			return nil, storagedriver.PathNotFoundError{Path: path}
		}
		data, err := d.blobs.GetUploadState(ctx, id, key)
		if errors.Is(err, storage.ErrNotExist) {
			return nil, storagedriver.PathNotFoundError{Path: path}
		}
		return data, err

	default:
		return d.getMetadataContent(ctx, path)
	}
}

func (d *DistDriver) getMetadataContent(ctx context.Context, path string) ([]byte, error) {
	repo := repoFromPath(path)
	if repo == "" {
		return nil, storagedriver.PathNotFoundError{Path: path}
	}
	repoID, err := d.meta.GetRepositoryID(ctx, repoNameFromString(repo))
	if err != nil {
		return nil, storagedriver.PathNotFoundError{Path: path}
	}
	dgst, err := d.resolveLink(ctx, repoID, path)
	if err != nil {
		return nil, storagedriver.PathNotFoundError{Path: path}
	}
	return []byte(dgst.String()), nil
}

func (d *DistDriver) resolveLink(ctx context.Context, repoID int64, path string) (digest.Digest, error) {
	if strings.Contains(path, "/tags/") && strings.HasSuffix(path, "/current/link") {
		return d.meta.GetTagDigest(ctx, repoID, tagFromPath(path))
	}
	if strings.Contains(path, "/_manifests/revisions/") && strings.HasSuffix(path, "/link") {
		dgst, err := digestFromLinkPath(path, "/_manifests/revisions/")
		if err != nil {
			return "", err
		}
		return d.meta.GetManifestDigest(ctx, repoID, dgst)
	}
	if strings.Contains(path, "/_layers/") && strings.HasSuffix(path, "/link") {
		dgst, err := digestFromLinkPath(path, "/_layers/")
		if err != nil {
			return "", err
		}
		// Check repo-scoped link first (manifestblob + uploadedblob),
		// then fall back to global existence (blob uploaded but not yet
		// linked to a manifest — distribution checks layers before
		// accepting the manifest that creates the link).
		if ok, _ := d.meta.BlobLinkedToRepo(ctx, repoID, dgst); ok {
			return dgst, nil
		}
		if ok, _ := d.meta.BlobExists(ctx, dgst); ok {
			return dgst, nil
		}
		return "", fmt.Errorf("blob not linked")
	}
	if strings.Contains(path, "/tags/") && strings.Contains(path, "/index/") && strings.HasSuffix(path, "/link") {
		dgst, err := digestFromLinkPath(path, "/index/")
		if err != nil {
			return "", err
		}
		return d.meta.GetManifestDigest(ctx, repoID, dgst)
	}
	return "", fmt.Errorf("unknown metadata path")
}

// PutContent writes small objects. Blob content is stored by digest,
// upload state goes to the upload directory. Metadata link writes are
// no-ops because the middleware already records them in SQLite.
func (d *DistDriver) PutContent(ctx context.Context, path string, content []byte) error {
	switch classify(path) {
	case pathBlob:
		dgst, err := digestFromBlobPath(path)
		if err != nil {
			return err
		}
		return d.blobs.PutContent(ctx, dgst, content)

	case pathUpload:
		id := uploadIDFromPath(path)
		key := uploadStateKey(path)
		if key == "" {
			return fmt.Errorf("cannot PutContent on upload data path: %s", path)
		}
		return d.blobs.PutUploadState(ctx, id, key, content)

	default:
		return nil // no-op — middleware handles metadata writes
	}
}

// Reader returns a streaming reader for blob content or upload data.
func (d *DistDriver) Reader(ctx context.Context, path string, offset int64) (io.ReadCloser, error) {
	switch classify(path) {
	case pathBlob:
		dgst, err := digestFromBlobPath(path)
		if err != nil {
			return nil, err
		}
		rc, err := d.blobs.Reader(ctx, dgst, offset)
		if errors.Is(err, storage.ErrNotExist) {
			return nil, storagedriver.PathNotFoundError{Path: path}
		}
		return rc, err

	case pathUpload:
		id := uploadIDFromPath(path)
		rc, err := d.blobs.UploadReader(ctx, id, offset)
		if errors.Is(err, storage.ErrNotExist) {
			return nil, storagedriver.PathNotFoundError{Path: path}
		}
		return rc, err

	default:
		return nil, storagedriver.PathNotFoundError{Path: path}
	}
}

// Writer returns a FileWriter for upload data. Distribution uses this
// to stream blob chunks during the upload lifecycle.
func (d *DistDriver) Writer(ctx context.Context, path string, appendMode bool) (storagedriver.FileWriter, error) {
	if classify(path) != pathUpload {
		return nil, fmt.Errorf("writer only supports upload paths: %s", path)
	}

	id := uploadIDFromPath(path)
	w, err := d.blobs.UploadWriter(ctx, id, appendMode)
	if err != nil {
		return nil, err
	}
	return &distFileWriter{w: w}, nil
}

// distFileWriter adapts oci.UploadWriter to distribution's storagedriver.FileWriter.
type distFileWriter struct {
	w oci.UploadWriter
}

func (fw *distFileWriter) Write(p []byte) (int, error)      { return fw.w.Write(p) }
func (fw *distFileWriter) Close() error                     { return fw.w.Close() }
func (fw *distFileWriter) Size() int64                      { return fw.w.Size() }
func (fw *distFileWriter) Commit(ctx context.Context) error { return fw.w.Commit(ctx) }
func (fw *distFileWriter) Cancel(ctx context.Context) error { return fw.w.Cancel(ctx) }

// Stat returns file info. Blob paths check content-addressed storage,
// upload paths check the staging directory, and metadata paths resolve
// links from SQLite and return a synthetic FileInfo.
func (d *DistDriver) Stat(ctx context.Context, path string) (storagedriver.FileInfo, error) {
	switch classify(path) {
	case pathBlob:
		dgst, err := digestFromBlobPath(path)
		if err != nil {
			return nil, err
		}
		info, err := d.blobs.Stat(ctx, dgst)
		if errors.Is(err, storage.ErrNotExist) {
			return nil, storagedriver.PathNotFoundError{Path: path}
		}
		if err != nil {
			return nil, err
		}
		return storagedriver.FileInfoInternal{FileInfoFields: storagedriver.FileInfoFields{
			Path: path, Size: info.Size, IsDir: false,
		}}, nil

	case pathUpload:
		id := uploadIDFromPath(path)
		rel := uploadRelPath(path)
		if strings.HasSuffix(rel, "/data") || rel == id {
			info, err := d.blobs.UploadStat(ctx, id)
			if errors.Is(err, storage.ErrNotExist) {
				return nil, storagedriver.PathNotFoundError{Path: path}
			}
			if err != nil {
				return nil, err
			}
			return storagedriver.FileInfoInternal{FileInfoFields: storagedriver.FileInfoFields{
				Path: path, Size: info.Size, IsDir: false,
			}}, nil
		}
		key := uploadStateKey(path)
		if key != "" {
			data, err := d.blobs.GetUploadState(ctx, id, key)
			if errors.Is(err, storage.ErrNotExist) {
				return nil, storagedriver.PathNotFoundError{Path: path}
			}
			if err != nil {
				return nil, err
			}
			return storagedriver.FileInfoInternal{FileInfoFields: storagedriver.FileInfoFields{
				Path: path, Size: int64(len(data)), IsDir: false,
			}}, nil
		}
		if _, err := d.blobs.UploadStat(ctx, id); err != nil {
			return nil, storagedriver.PathNotFoundError{Path: path}
		}
		return storagedriver.FileInfoInternal{FileInfoFields: storagedriver.FileInfoFields{
			Path: path, IsDir: true,
		}}, nil

	default:
		return d.statMetadata(ctx, path)
	}
}

// statMetadata resolves metadata paths for distribution's Walk tree traversal.
// It handles link files (tags, layers, manifest revisions), repo directories,
// namespace directories, and the _manifests sentinel directory.
func (d *DistDriver) statMetadata(ctx context.Context, path string) (storagedriver.FileInfo, error) {
	if content, err := d.getMetadataContent(ctx, path); err == nil {
		return storagedriver.FileInfoInternal{FileInfoFields: storagedriver.FileInfoFields{
			Path: path, Size: int64(len(content)), IsDir: false,
		}}, nil
	}

	// Virtual directories for Walk tree traversal: _manifests, repo dirs,
	// namespace dirs, and the repositories root all appear as directories.
	if d.isVirtualDir(ctx, path) {
		return storagedriver.FileInfoInternal{FileInfoFields: storagedriver.FileInfoFields{
			Path: path, IsDir: true,
		}}, nil
	}
	return nil, storagedriver.PathNotFoundError{Path: path}
}

// isVirtualDir returns true if the path represents a directory in the
// virtual filesystem tree that distribution's Walk expects. This includes
// the repositories root, namespace prefixes, repository dirs, and the
// _manifests sentinel within each repo.
func (d *DistDriver) isVirtualDir(ctx context.Context, path string) bool {
	if strings.HasSuffix(path, "/repositories") || strings.HasSuffix(path, "/repositories/") {
		return true
	}

	// _manifests or _manifests/tags under a known repo
	repo := repoFromPath(path)
	if repo != "" && (strings.HasSuffix(path, "/_manifests") || strings.HasSuffix(path, "/_manifests/tags")) {
		_, err := d.meta.GetRepositoryID(ctx, repoNameFromString(repo))
		return err == nil
	}

	// The path after /repositories/ might be a complete repo name or just
	// a namespace prefix. Check both.
	prefix := d.repoPrefixFromPath(strings.TrimSuffix(path, "/"))
	if prefix == "" {
		return false
	}

	// Known repo — the directory exists.
	if _, err := d.meta.GetRepositoryID(ctx, repoNameFromString(prefix)); err == nil {
		return true
	}

	// Namespace prefix — at least one repo starts with this path segment.
	return d.isNamespacePrefix(ctx, path)
}

// List returns direct children of a path. Upload directories list state
// files, tag directories list tag names from SQLite, and repository tree
// paths return virtual directory entries for distribution's Walk traversal.
func (d *DistDriver) List(ctx context.Context, path string) ([]string, error) {
	if classify(path) == pathUpload {
		return d.listUploadState(ctx, path)
	}
	if strings.HasSuffix(path, "/_manifests/tags") || strings.HasSuffix(path, "/_manifests/tags/") {
		return d.listTags(ctx, path)
	}
	return d.listRepoTree(ctx, path)
}

func (d *DistDriver) listUploadState(ctx context.Context, path string) ([]string, error) {
	id := uploadIDFromPath(path)
	key := uploadStateKey(path)
	if key == "" {
		key = strings.TrimPrefix(uploadRelPath(path), id+"/")
	}
	if key == "" || key == id {
		key = ""
	}
	keys, err := d.blobs.ListUploadState(ctx, id, key)
	if err != nil {
		return nil, storagedriver.PathNotFoundError{Path: path}
	}
	return prefixAll(path, keys), nil
}

func (d *DistDriver) listTags(ctx context.Context, path string) ([]string, error) {
	repo := repoFromPath(path)
	name := repoNameFromString(repo)
	repoID, err := d.meta.GetRepositoryID(ctx, name)
	if err != nil {
		return nil, storagedriver.PathNotFoundError{Path: path}
	}
	tags, err := d.meta.ListTags(ctx, repoID)
	if err != nil {
		return nil, err
	}
	return prefixAll(path, tags), nil
}

// listRepoTree returns virtual directory children for distribution's Walk.
// The repositories root returns unique first-level segments (namespaces),
// a namespace prefix returns next-level segments, and a complete repo
// path returns the _manifests sentinel that distribution uses to identify
// repository directories.
//
// TODO: ListRepositories is an unbounded full table scan called here and from
// isNamespacePrefix. Fine at mirror-registry scale (~20 repos); for multi-tenant
// use, add a ListRepositoriesByPrefix query with a LIKE filter.
func (d *DistDriver) listRepoTree(ctx context.Context, path string) ([]string, error) {
	clean := strings.TrimSuffix(path, "/")

	// If path ends at a known repo, return _manifests.
	repo := repoFromPath(path)
	if repo != "" {
		if _, err := d.meta.GetRepositoryID(ctx, repoNameFromString(repo)); err == nil {
			return []string{clean + "/_manifests"}, nil
		}
	}

	// Find the prefix relative to /repositories/ to match against repo names.
	prefix := d.repoPrefixFromPath(clean)

	repos, err := d.meta.ListRepositories(ctx)
	if err != nil {
		return nil, err
	}

	// Collect unique direct children under this prefix.
	seen := make(map[string]struct{})
	for _, r := range repos {
		full := r.String()
		if prefix != "" {
			if !strings.HasPrefix(full, prefix+"/") {
				continue
			}
			full = full[len(prefix)+1:]
		}
		if seg, _, ok := strings.Cut(full, "/"); ok {
			seen[seg] = struct{}{}
		} else {
			seen[full] = struct{}{}
		}
	}

	if len(seen) == 0 {
		return nil, storagedriver.PathNotFoundError{Path: path}
	}

	result := make([]string, 0, len(seen))
	for seg := range seen {
		result = append(result, clean+"/"+seg)
	}
	sort.Strings(result)
	return result, nil
}

// repoPrefixFromPath extracts the path segments between /repositories/ and the
// end of the path. For "/docker/registry/v2/repositories/admin" it returns "admin".
// For the repositories root itself it returns "".
func (d *DistDriver) repoPrefixFromPath(path string) string {
	const marker = "/repositories/"
	idx := strings.Index(path, marker)
	if idx < 0 {
		return ""
	}
	after := path[idx+len(marker):]
	return strings.TrimSuffix(after, "/")
}

// isNamespacePrefix returns true if any repository name starts with the
// path segments after /repositories/.
func (d *DistDriver) isNamespacePrefix(ctx context.Context, path string) bool {
	prefix := d.repoPrefixFromPath(strings.TrimSuffix(path, "/"))
	if prefix == "" {
		return false
	}
	repos, err := d.meta.ListRepositories(ctx)
	if err != nil {
		return false
	}
	for _, r := range repos {
		if strings.HasPrefix(r.String(), prefix+"/") || r.String() == prefix {
			return true
		}
	}
	return false
}

func prefixAll(basePath string, items []string) []string {
	base := strings.TrimSuffix(basePath, "/")
	result := make([]string, len(items))
	for i, item := range items {
		result[i] = base + "/" + item
	}
	return result
}

// Move finalizes an upload by streaming the staged data through the
// BlobStore's content-addressed writer, then cleaning up the upload.
// Only upload-to-blob moves are supported.
func (d *DistDriver) Move(ctx context.Context, src, dst string) error {
	srcKind := classify(src)
	dstKind := classify(dst)

	if srcKind == pathUpload && dstKind == pathBlob {
		dgst, err := digestFromBlobPath(dst)
		if err != nil {
			return err
		}
		id := uploadIDFromPath(src)
		rc, err := d.blobs.UploadReader(ctx, id, 0)
		if errors.Is(err, storage.ErrNotExist) {
			return storagedriver.PathNotFoundError{Path: src}
		}
		if err != nil {
			return err
		}
		defer func() { _ = rc.Close() }()

		w, err := d.blobs.Writer(ctx, dgst)
		if err != nil {
			return err
		}
		if _, err := io.Copy(w, rc); err != nil {
			if cerr := w.Close(); cerr != nil {
				return fmt.Errorf("copy failed: %w (close also failed: %w)", err, cerr)
			}
			return err
		}
		if err := w.Close(); err != nil {
			return err
		}

		return d.blobs.CancelUpload(ctx, id)
	}

	return fmt.Errorf("unsupported move: %s → %s", src, dst)
}

// Delete removes blobs by digest, upload directories by canceling the
// upload, and is a no-op for metadata (handled by the middleware).
func (d *DistDriver) Delete(ctx context.Context, path string) error {
	switch classify(path) {
	case pathBlob:
		dgst, err := digestFromBlobPath(path)
		if err != nil {
			return err
		}
		err = d.blobs.Delete(ctx, dgst)
		if errors.Is(err, storage.ErrNotExist) {
			return storagedriver.PathNotFoundError{Path: path}
		}
		return err

	case pathUpload:
		id := uploadIDFromPath(path)
		err := d.blobs.CancelUpload(ctx, id)
		if errors.Is(err, storage.ErrNotExist) {
			return storagedriver.PathNotFoundError{Path: path}
		}
		return err

	default:
		return nil // metadata deletion handled by middleware
	}
}

// RedirectURL returns empty — local storage serves content directly.
func (d *DistDriver) RedirectURL(_ *http.Request, _ string) (string, error) {
	return "", nil
}

// Walk traverses the virtual filesystem using List and Stat. Distribution
// calls this for catalog enumeration and garbage collection.
func (d *DistDriver) Walk(ctx context.Context, path string, f storagedriver.WalkFn, opts ...func(*storagedriver.WalkOptions)) error {
	return storagedriver.WalkFallback(ctx, d, path, f, opts...)
}

// repoNameFromString splits "namespace/name" into an oci.RepositoryName.
func repoNameFromString(s string) oci.RepositoryName {
	if i := strings.IndexByte(s, '/'); i >= 0 {
		return oci.RepositoryName{Namespace: s[:i], Name: s[i+1:]}
	}
	return oci.RepositoryName{Name: s}
}

// tagFromPath extracts the tag name from a tag current link path.
func tagFromPath(path string) string {
	const marker = "/tags/"
	idx := strings.LastIndex(path, marker)
	if idx < 0 {
		return ""
	}
	remainder := path[idx+len(marker):]
	if slash := strings.IndexByte(remainder, '/'); slash >= 0 {
		return remainder[:slash]
	}
	return remainder
}

// digestFromLinkPath extracts a digest from a link path after a known segment.
func digestFromLinkPath(path, segment string) (digest.Digest, error) {
	idx := strings.Index(path, segment)
	if idx < 0 {
		return "", fmt.Errorf("segment %q not found in %s", segment, path)
	}
	remainder := path[idx+len(segment):]
	remainder = strings.TrimSuffix(remainder, "/link")
	parts := strings.SplitN(remainder, "/", 2)
	if len(parts) < 2 {
		return "", fmt.Errorf("malformed link path: %s", path)
	}
	return digest.Parse(parts[0] + ":" + parts[1])
}

// uploadStateKey extracts the state key from an upload path.
// Returns "" for the data file itself (handled by UploadWriter/UploadReader).
//
//	.../_uploads/<id>/startedat              → "startedat"
//	.../_uploads/<id>/hashstates/sha256/1024 → "hashstates/sha256/1024"
//	.../_uploads/<id>/data                   → ""
func uploadStateKey(path string) string {
	rel := uploadRelPath(path)
	slash := strings.IndexByte(rel, '/')
	if slash < 0 {
		return ""
	}
	key := rel[slash+1:]
	if key == "data" {
		return ""
	}
	return key
}
