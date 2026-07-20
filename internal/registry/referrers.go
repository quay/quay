// Package registry implements OCI registry endpoints not covered by distribution/v3.
package registry

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"regexp"
	"strings"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/repository"
	repositorydal "github.com/quay/quay/internal/repository/dal"
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
	LibraryNamespace                   string
	AnonymousAccess                    bool
	LibrarySupport                     bool
	DatabaseSecretKey                  string
	RobotsDisallow                     bool
	RobotsWhitelist                    []string
	FeatureUserLastAccessed            bool
	LastAccessedUpdateThresholdSeconds int
	SuperUsers                         []string
	SuperUsersFullAccess               bool
	Authenticator                      oci.Authenticator
	TokenRealm                         string
	TokenService                       string
}

// ReferrersHandler serves the OCI referrers API.
type ReferrersHandler struct {
	store         oci.MetadataStore
	authenticator *auth.BasicAuthenticator
	bearerAuth    oci.Authenticator
	authorizer    *repositorydal.Authorizer
	queries       *daldb.Queries
	config        ReferrersConfig
}

// NewReferrersHandler creates a handler for GET /v2/{name}/referrers/{digest}.
func NewReferrersHandler(db *sql.DB, store oci.MetadataStore, cfg *ReferrersConfig) *ReferrersHandler {
	config := ReferrersConfig{}
	if cfg != nil {
		config = *cfg
	}
	if config.LibraryNamespace == "" {
		config.LibraryNamespace = defaultLibraryNamespace
	}
	return &ReferrersHandler{
		store: store,
		authenticator: auth.NewBasicAuthenticator(auth.NewDatabaseVerifier(db, auth.DatabaseVerifierConfig{
			DatabaseSecretKey:              config.DatabaseSecretKey,
			RobotsDisallow:                 config.RobotsDisallow,
			RobotsWhitelist:                config.RobotsWhitelist,
			FeatureUserLastAccessed:        config.FeatureUserLastAccessed,
			LastAccessedUpdateThresholdSec: config.LastAccessedUpdateThresholdSeconds,
		})),
		authorizer: repositorydal.NewAuthorizer(db, repositorydal.AuthorizerConfig{
			SuperUsers:           config.SuperUsers,
			SuperUsersFullAccess: config.SuperUsersFullAccess,
		}),
		queries:    daldb.New(db),
		bearerAuth: config.Authenticator,
		config:     config,
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

	allowed, authErr := h.authorize(r, namespace, repo)
	if !allowed {
		var challenge oci.AuthChallenge
		switch {
		case errors.As(authErr, &challenge):
			challenge.SetHeaders(w)
		case h.config.TokenRealm != "" && h.config.TokenService != "":
			w.Header().Set("WWW-Authenticate", fmt.Sprintf(
				`Bearer realm=%q,service=%q,scope=%q`,
				h.config.TokenRealm, h.config.TokenService, "repository:"+name+":pull",
			))
		default:
			w.Header().Set("WWW-Authenticate", `Basic realm="quay"`)
		}
		writeOCIError(w, http.StatusUnauthorized, "UNAUTHORIZED", "authentication required")
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

func (h *ReferrersHandler) authorize(r *http.Request, namespace, repo string) (bool, error) {
	if h.bearerAuth != nil {
		_, err := h.bearerAuth.Authenticate(r, oci.Access{
			Resource: "repository:" + namespace + "/" + repo,
			Action:   "pull",
		})
		return err == nil, err
	}
	if h.authenticator == nil {
		return h.config.AnonymousAccess, nil
	}
	result := h.authenticator.Authenticate(r)
	if result.Authenticated {
		return h.canPullRepository(r, &result.Principal, namespace, repo), nil
	}
	if result.Presented {
		return false, oci.ErrUnauthorized
	}
	if h.config.AnonymousAccess && h.queries != nil {
		isPublic, err := h.queries.RepositoryIsPublicByNamespaceName(r.Context(), daldb.RepositoryIsPublicByNamespaceNameParams{
			Username: namespace,
			Name:     repo,
		})
		if err == nil && isPublic != 0 {
			return true, nil
		}
	}
	return false, oci.ErrUnauthorized
}

func (h *ReferrersHandler) canPullRepository(r *http.Request, principal *auth.Principal, namespace, repoName string) bool {
	if h.queries == nil || h.authorizer == nil {
		return false
	}

	row, err := h.queries.GetRepositoryAccessByNamespaceName(r.Context(), daldb.GetRepositoryAccessByNamespaceNameParams{
		Username: namespace,
		Name:     repoName,
	})
	if err != nil {
		slog.Debug("referrers repository lookup failed", "namespace", namespace, "repository", repoName, "err", err)
		return false
	}

	repo := repository.Repository{
		ID: row.ID,
		Ref: repository.Ref{
			Namespace: row.Namespace,
			Name:      row.Name,
		},
		Visibility:       repository.Visibility(row.Visibility),
		State:            row.State,
		KindID:           row.KindID,
		NamespaceEnabled: row.NamespaceEnabled,
	}
	allowed, err := h.authorizer.CanPullRepository(r.Context(), principal, &repo)
	if err != nil {
		slog.Debug("referrers pull authorization failed", "namespace", namespace, "repository", repoName, "err", err)
		return false
	}
	return allowed
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
