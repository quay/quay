// Package registry implements OCI registry endpoints not covered by distribution/v3.
package registry

import (
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"regexp"
	"strings"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci"
)

const (
	ociImageIndexMediaType  = "application/vnd.oci.image.index.v1+json"
	defaultLibraryNamespace = "library"
)

var (
	referrersPathRe      = regexp.MustCompile(`^/v2/(.+)/referrers/(` + digest.DigestRegexp.String() + `)$`)
	referrersPathLooseRe = regexp.MustCompile(`^/v2/.+/referrers/.+$`)
)

// ReferrersConfig holds the configuration for the referrers handler.
type ReferrersConfig struct {
	LibraryNamespace string
	LibrarySupport   bool
}

// ReferrersHandler serves the OCI referrers API.
type ReferrersHandler struct {
	store      oci.MetadataStore
	controller RepositoryAccessController
	config     ReferrersConfig
}

// RepositoryAccessController authorizes one action against a repository.
type RepositoryAccessController interface {
	AuthorizeRepository(req *http.Request, name, action string) error
}

// NewReferrersHandler creates a handler for GET /v2/{name}/referrers/{digest}.
func NewReferrersHandler(store oci.MetadataStore, controller RepositoryAccessController, cfg *ReferrersConfig) *ReferrersHandler {
	config := ReferrersConfig{}
	if cfg != nil {
		config = *cfg
	}
	if config.LibraryNamespace == "" {
		config.LibraryNamespace = defaultLibraryNamespace
	}
	return &ReferrersHandler{
		store: store, controller: controller, config: config,
	}
}

// Matches reports whether the request targets the referrers endpoint.
func (h *ReferrersHandler) Matches(r *http.Request) bool {
	return r.Method == http.MethodGet && referrersPathLooseRe.MatchString(r.URL.Path)
}

func (h *ReferrersHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	matches := referrersPathRe.FindStringSubmatch(r.URL.Path)
	if matches == nil {
		writeOCIError(w, http.StatusBadRequest, "DIGEST_INVALID", "invalid digest")
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

	if err := h.authorize(r, namespace, repo); err != nil {
		var challenge authenticationChallenge
		if errors.As(err, &challenge) {
			challenge.SetHeaders(r, w)
			writeOCIError(w, http.StatusUnauthorized, "UNAUTHORIZED", "authentication required")
			return
		}
		slog.Error("referrers authorization failed", "repository", name, "err", err) //nolint:gosec // structured logging, not injection
		writeOCIError(w, http.StatusInternalServerError, "UNKNOWN", "internal error")
		return
	}

	repoID, err := h.store.GetRepositoryID(r.Context(), oci.RepositoryName{
		Namespace: namespace,
		Name:      repo,
	})
	if err != nil {
		if errors.Is(err, oci.ErrNotExist) {
			writeOCIError(w, http.StatusNotFound, "NAME_UNKNOWN", "repository name not known to registry")
			return
		}
		slog.Error("get repository id failed", "repository", name, "err", err) //nolint:gosec // structured logging, not injection
		writeOCIError(w, http.StatusInternalServerError, "UNKNOWN", "internal error")
		return
	}

	queryParams := r.URL.Query()
	artifactType := queryParams.Get("artifactType")
	_, filterPresent := queryParams["artifactType"]

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
			Annotations:  ref.Annotations,
		})
	}

	resp := ociIndex{
		SchemaVersion: 2,
		MediaType:     ociImageIndexMediaType,
		Manifests:     manifests,
	}

	w.Header().Set("Content-Type", ociImageIndexMediaType)
	if filterPresent {
		w.Header().Set("OCI-Filters-Applied", "artifactType")
	}
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)
}

func (h *ReferrersHandler) splitName(name string) (namespace, repo string) {
	i := strings.IndexByte(name, '/')
	if i < 0 {
		if !h.config.LibrarySupport {
			return "", ""
		}
		return h.config.LibraryNamespace, name
	}
	return name[:i], name[i+1:]
}

func (h *ReferrersHandler) authorize(r *http.Request, namespace, repo string) error {
	if h.controller == nil {
		return fmt.Errorf("nil access controller")
	}
	return h.controller.AuthorizeRepository(r, namespace+"/"+repo, "pull")
}

type authenticationChallenge interface {
	error
	SetHeaders(*http.Request, http.ResponseWriter)
}

type ociIndex struct {
	SchemaVersion int             `json:"schemaVersion"`
	MediaType     string          `json:"mediaType"`
	Manifests     []ociDescriptor `json:"manifests"`
}

type ociDescriptor struct {
	MediaType    string            `json:"mediaType"`
	Digest       string            `json:"digest"`
	Size         int64             `json:"size"`
	ArtifactType string            `json:"artifactType,omitempty"`
	Annotations  map[string]string `json:"annotations,omitempty"`
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
