package auth

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

const maximumTokenQueryBytes = 64 << 10

// HandlerConfig configures GET /v2/auth.
type HandlerConfig struct {
	Service          string
	LibraryNamespace string
	AnonymousAccess  bool
	Lifetime         time.Duration
	Signer           TokenSigner
	Authenticate     AuthenticateFunc
	ResolveGrants    GrantResolver
	Now              func() time.Time
}

// Handler exchanges Quay Basic credentials for short-lived scoped tokens.
type Handler struct {
	service          string
	libraryNamespace string
	anonymousAccess  bool
	lifetime         time.Duration
	signer           TokenSigner
	authenticate     AuthenticateFunc
	resolveGrants    GrantResolver
	now              func() time.Time
}

// NewHandler constructs a token exchange handler.
func NewHandler(cfg *HandlerConfig) (*Handler, error) {
	if cfg == nil {
		return nil, fmt.Errorf("nil handler config")
	}
	if cfg.Service == "" || cfg.LibraryNamespace == "" || cfg.Signer == nil || cfg.ResolveGrants == nil {
		return nil, fmt.Errorf("service, library namespace, signer, and grant resolver are required")
	}
	if cfg.Lifetime < minimumTokenLifetime {
		return nil, fmt.Errorf("token lifetime must be at least %s", minimumTokenLifetime)
	}
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	return &Handler{
		service:          cfg.Service,
		libraryNamespace: cfg.LibraryNamespace,
		anonymousAccess:  cfg.AnonymousAccess,
		lifetime:         cfg.Lifetime,
		signer:           cfg.Signer,
		authenticate:     cfg.Authenticate,
		resolveGrants:    cfg.ResolveGrants,
		now:              cfg.Now,
	}, nil
}

func (h *Handler) ServeHTTP(response http.ResponseWriter, request *http.Request) {
	setNoCacheHeaders(response)
	if request.Method != http.MethodGet {
		response.Header().Set("Allow", http.MethodGet)
		writeTokenError(response, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}
	if len(request.URL.RawQuery) > maximumTokenQueryBytes {
		writeTokenError(response, http.StatusBadRequest, "invalid_scope")
		return
	}

	query := request.URL.Query()
	services := query["service"]
	if len(services) != 1 || services[0] != h.service {
		writeTokenError(response, http.StatusBadRequest, "invalid_service")
		return
	}
	requested, err := ParseScopes(query["scope"], h.service, h.libraryNamespace)
	if err != nil {
		writeTokenError(response, http.StatusBadRequest, "invalid_scope")
		return
	}

	identity, ok := h.authenticateRequest(request)
	if !ok {
		response.Header().Set("WWW-Authenticate", `Basic realm=`+quoteHeader(h.service))
		writeTokenError(response, http.StatusUnauthorized, "invalid_client")
		return
	}

	access, err := h.resolveGrants(request.Context(), identity, requested)
	if err != nil {
		writeTokenError(response, http.StatusInternalServerError, "server_error")
		return
	}
	if access == nil {
		access = []ResourceActions{}
	}

	now := h.now().UTC().Truncate(time.Second)
	jti, err := randomTokenID()
	if err != nil {
		writeTokenError(response, http.StatusInternalServerError, "server_error")
		return
	}
	claims := &Claims{
		Issuer: Issuer, Subject: identity.Subject, Audience: h.service,
		IssuedAt: now.Unix(), NotBefore: now.Unix(), Expiration: now.Add(h.lifetime).Unix(),
		JWTID: jti, Access: access,
	}
	token, err := h.signer.Sign(claims)
	if err != nil {
		writeTokenError(response, http.StatusInternalServerError, "server_error")
		return
	}

	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(response).Encode(map[string]any{
		"token": token, "access_token": token, "expires_in": int64(h.lifetime / time.Second),
		"issued_at": now.Format(time.RFC3339),
	})
}

func (h *Handler) authenticateRequest(request *http.Request) (Identity, bool) {
	header := strings.TrimSpace(request.Header.Get("Authorization"))
	if header == "" {
		if !h.anonymousAccess {
			return Identity{}, false
		}
		return Identity{Subject: AnonymousSubject, Anonymous: true}, true
	}
	fields := strings.Fields(header)
	if len(fields) != 2 || !strings.EqualFold(fields[0], "Basic") {
		return Identity{}, false
	}
	username, secret, ok := request.BasicAuth()
	if !ok || h.authenticate == nil {
		return Identity{}, false
	}
	identity, ok := h.authenticate(request.Context(), username, secret)
	if !ok || identity.Subject == "" || identity.Anonymous {
		return Identity{}, false
	}
	return identity, true
}

func setNoCacheHeaders(response http.ResponseWriter) {
	response.Header().Set("Cache-Control", "no-store")
	response.Header().Set("Pragma", "no-cache")
}

func writeTokenError(response http.ResponseWriter, status int, code string) {
	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(status)
	_ = json.NewEncoder(response).Encode(map[string]string{"error": code})
}

func randomTokenID() (string, error) {
	value := make([]byte, 16)
	if _, err := rand.Read(value); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(value), nil
}

func quoteHeader(value string) string {
	encoded, _ := json.Marshal(value)
	return string(encoded)
}
