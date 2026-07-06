// Package registry implements OCI registry endpoints not covered by distribution/v3.
package registry

import (
	"database/sql"
	"encoding/json"
	"log/slog"
	"net/http"
	"regexp"
	"strings"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/oci"
)

const ociImageIndexMediaType = "application/vnd.oci.image.index.v1+json"

var referrersPathRe = regexp.MustCompile(`^/v2/(.+)/referrers/(` + digest.DigestRegexp.String() + `)$`)

// ReferrersConfig holds the configuration for the referrers handler.
type ReferrersConfig struct {
	LibraryNamespace string
	AnonymousAccess  bool
}

// ReferrersHandler serves the OCI referrers API.
type ReferrersHandler struct {
	store         oci.MetadataStore
	authenticator *auth.BasicAuthenticator
	queries       *daldb.Queries
	config        ReferrersConfig
}

// NewReferrersHandler creates a handler for GET /v2/{name}/referrers/{digest}.
func NewReferrersHandler(db *sql.DB, store oci.MetadataStore, cfg ReferrersConfig) *ReferrersHandler {
	if cfg.LibraryNamespace == "" {
		cfg.LibraryNamespace = "library"
	}
	return &ReferrersHandler{
		store:         store,
		authenticator: auth.NewBasicAuthenticator(db),
		queries:       daldb.New(db),
		config:        cfg,
	}
}

// Matches reports whether the request targets the referrers endpoint.
func (h *ReferrersHandler) Matches(r *http.Request) bool {
	return r.Method == http.MethodGet && referrersPathRe.MatchString(r.URL.Path)
}

func (h *ReferrersHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	matches := referrersPathRe.FindStringSubmatch(r.URL.Path)
	if matches == nil {
		http.NotFound(w, r)
		return
	}

	name := matches[1]
	dgstStr := matches[2]

	dgst, err := digest.Parse(dgstStr)
	if err != nil {
		writeOCIError(w, http.StatusBadRequest, "DIGEST_INVALID", "invalid digest")
		return
	}

	namespace, repo := h.splitName(name)
	if namespace == "" || repo == "" {
		writeOCIError(w, http.StatusNotFound, "NAME_UNKNOWN", "repository name not known to registry")
		return
	}

	if !h.authorize(r, namespace, repo) {
		w.Header().Set("WWW-Authenticate", `Basic realm="quay"`)
		writeOCIError(w, http.StatusUnauthorized, "UNAUTHORIZED", "authentication required")
		return
	}

	repoID, err := h.store.GetRepositoryID(r.Context(), oci.RepositoryName{
		Namespace: namespace,
		Name:      repo,
	})
	if err != nil {
		writeOCIError(w, http.StatusNotFound, "NAME_UNKNOWN", "repository name not known to registry")
		return
	}

	artifactType := r.URL.Query().Get("artifactType")

	referrers, err := h.store.ListReferrers(r.Context(), repoID, dgst, artifactType)
	if err != nil {
		slog.Error("list referrers failed", "repository", name, "digest", dgst, "err", err) //nolint:gosec // structured logging, not injection
		writeOCIError(w, http.StatusInternalServerError, "UNKNOWN", "internal error")
		return
	}

	manifests := make([]ociDescriptor, 0, len(referrers))
	for _, ref := range referrers {
		manifests = append(manifests, ociDescriptor{
			MediaType:    ref.MediaType,
			Digest:       ref.Digest,
			Size:         ref.Size,
			ArtifactType: ref.ArtifactType,
		})
	}

	resp := ociIndex{
		SchemaVersion: 2,
		MediaType:     ociImageIndexMediaType,
		Manifests:     manifests,
	}

	w.Header().Set("Content-Type", ociImageIndexMediaType)
	if artifactType != "" {
		w.Header().Set("OCI-Filters-Applied", "artifactType")
	}
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)
}

func (h *ReferrersHandler) splitName(name string) (namespace, repo string) {
	i := strings.IndexByte(name, '/')
	if i < 0 {
		return h.config.LibraryNamespace, name
	}
	return name[:i], name[i+1:]
}

func (h *ReferrersHandler) authorize(r *http.Request, namespace, repo string) bool {
	if h.authenticator == nil {
		return h.config.AnonymousAccess
	}
	result := h.authenticator.Authenticate(r)
	if result.Authenticated {
		return true
	}
	if result.Presented {
		return false
	}
	if h.config.AnonymousAccess && h.queries != nil {
		isPublic, err := h.queries.RepositoryIsPublicByNamespaceName(r.Context(), daldb.RepositoryIsPublicByNamespaceNameParams{
			Username: namespace,
			Name:     repo,
		})
		if err == nil && isPublic == 1 {
			return true
		}
	}
	return false
}

type ociIndex struct {
	SchemaVersion int             `json:"schemaVersion"`
	MediaType     string          `json:"mediaType"`
	Manifests     []ociDescriptor `json:"manifests"`
}

type ociDescriptor struct {
	MediaType    string `json:"mediaType"`
	Digest       string `json:"digest"`
	Size         int64  `json:"size"`
	ArtifactType string `json:"artifactType,omitempty"`
}

func writeOCIError(w http.ResponseWriter, status int, code, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"errors": []map[string]string{
			{"code": code, "message": message},
		},
	})
}

// WrapWithReferrers returns an http.Handler that intercepts referrers requests
// and delegates everything else to the fallback handler.
func WrapWithReferrers(referrers *ReferrersHandler, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if referrers.Matches(r) {
			referrers.ServeHTTP(w, r)
			return
		}
		fallback.ServeHTTP(w, r)
	})
}
