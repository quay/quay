package distribution

import (
	"encoding/json"
	"fmt"
	"net/http"
	"slices"
	"strings"
	"time"

	distauth "github.com/distribution/distribution/v3/registry/auth"

	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/registry/jwtauth"
)

// TokenHandler authenticates Basic credentials and exchanges them for scoped
// Docker Registry Bearer tokens.
type TokenHandler struct {
	credentials     credentialAuthenticator
	policy          repositoryAccessPolicy
	issuer          tokenIssuer
	anonymousAccess bool
}

const (
	maxRequestedScopeCount = 100
	maxRequestedScopeBytes = 16 << 10
)

type credentialAuthenticator interface {
	Authenticate(*http.Request) auth.Result
}

type repositoryAccessPolicy interface {
	AuthorizeRepositoryAccess(*http.Request, *auth.Principal, distauth.Access, []distauth.Access) error
}

type tokenIssuer interface {
	Audience() string
	Lifetime() time.Duration
	Issue(string, []jwtauth.ResourceActions) (string, time.Time, error)
}

type controllerTokenPolicy struct{ controller *accessController }

func (p controllerTokenPolicy) AuthorizeRepositoryAccess(r *http.Request, principal *auth.Principal, item distauth.Access, all []distauth.Access) error {
	return p.controller.authorizeRepositoryAccess(r, principal, item, all)
}

func newTokenHandler(credentials credentialAuthenticator, policy repositoryAccessPolicy, issuer tokenIssuer, anonymousAccess bool) (*TokenHandler, error) {
	if credentials == nil {
		return nil, fmt.Errorf("token handler requires a credential authenticator")
	}
	if policy == nil {
		return nil, fmt.Errorf("token handler requires a repository access policy")
	}
	if issuer == nil {
		return nil, fmt.Errorf("token handler requires a JWT service")
	}
	return &TokenHandler{
		credentials: credentials, policy: policy, issuer: issuer, anonymousAccess: anonymousAccess,
	}, nil
}

func (h *TokenHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", http.MethodGet)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if requestedService := r.URL.Query().Get("service"); requestedService != "" && requestedService != h.issuer.Audience() {
		http.Error(w, "invalid token service", http.StatusBadRequest)
		return
	}

	principal, ok := h.authenticate(w, r)
	if !ok {
		return
	}
	if account := r.URL.Query().Get("account"); account != "" && account != principal.Username {
		h.basicChallenge(w)
		return
	}

	requested, err := parseRequestedScopes(r)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	authorized := h.downscope(r, principal, requested)
	subject := principal.Username
	if principal.IsAnonymous() {
		subject = jwtauth.AnonymousSubject
	}
	raw, expiresAt, err := h.issuer.Issue(subject, authorized)
	if err != nil {
		http.Error(w, "could not issue token", http.StatusInternalServerError)
		return
	}
	issuedAt := expiresAt.Add(-h.issuer.Lifetime())
	response := struct {
		Token       string `json:"token"`
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
		IssuedAt    string `json:"issued_at"`
	}{
		Token: raw, AccessToken: raw,
		ExpiresIn: int64(h.issuer.Lifetime() / time.Second),
		IssuedAt:  issuedAt.Format(time.RFC3339),
	}
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(response) //nolint:gosec // access_token is a required Docker token response field
}

func (h *TokenHandler) authenticate(w http.ResponseWriter, r *http.Request) (*auth.Principal, bool) {
	result := h.credentials.Authenticate(r)
	if result.Authenticated {
		return &result.Principal, true
	}
	if result.Presented || !h.anonymousAccess || r.URL.Query().Get("account") != "" || !hasRequestedScope(r) {
		h.basicChallenge(w)
		return nil, false
	}
	return auth.AnonymousPrincipal(), true
}

func hasRequestedScope(r *http.Request) bool {
	for _, value := range r.URL.Query()["scope"] {
		if len(strings.Fields(value)) > 0 {
			return true
		}
	}
	return false
}

func (h *TokenHandler) basicChallenge(w http.ResponseWriter) {
	w.Header().Set("WWW-Authenticate", fmt.Sprintf("Basic realm=%q", h.issuer.Audience()))
	http.Error(w, "invalid credentials", http.StatusUnauthorized)
}

func parseRequestedScopes(r *http.Request) ([]jwtauth.ResourceActions, error) {
	var scopes []string
	totalBytes := 0
	for _, value := range r.URL.Query()["scope"] {
		totalBytes += len(value)
		if totalBytes > maxRequestedScopeBytes {
			return nil, fmt.Errorf("requested scopes exceed %d bytes", maxRequestedScopeBytes)
		}
		fields := strings.Fields(value)
		if len(scopes)+len(fields) > maxRequestedScopeCount {
			return nil, fmt.Errorf("too many requested scopes")
		}
		scopes = append(scopes, fields...)
	}
	requested := make([]jwtauth.ResourceActions, 0, len(scopes))
	for _, scope := range scopes {
		parts := strings.SplitN(scope, ":", 3)
		if len(parts) != 3 || parts[0] != repositoryResourceType || parts[1] == "" || parts[2] == "" {
			return nil, fmt.Errorf("invalid scope %q", scope)
		}
		actions := strings.Split(parts[2], ",")
		for _, action := range actions {
			if action != repositoryPullAction && action != repositoryPushAction && action != jwtauth.WildcardAction {
				return nil, fmt.Errorf("invalid scope action %q", action)
			}
		}
		requested = append(requested, jwtauth.ResourceActions{
			Type: parts[0], Name: parts[1], Actions: actions,
		})
	}
	return mergeAccess(requested), nil
}

func (h *TokenHandler) downscope(r *http.Request, principal *auth.Principal, requested []jwtauth.ResourceActions) []jwtauth.ResourceActions {
	allRequested := make([]distauth.Access, 0)
	for _, grant := range requested {
		for _, action := range grant.Actions {
			if action == jwtauth.WildcardAction {
				allRequested = append(allRequested,
					repositoryAccessItem(grant.Name, repositoryPullAction),
					repositoryAccessItem(grant.Name, repositoryPushAction),
				)
				continue
			}
			allRequested = append(allRequested, repositoryAccessItem(grant.Name, action))
		}
	}

	authorized := make([]jwtauth.ResourceActions, 0, len(requested))
	for _, grant := range requested {
		allowed := jwtauth.ResourceActions{Type: grant.Type, Name: grant.Name}
		pushRequested := slices.Contains(grant.Actions, repositoryPushAction) || slices.Contains(grant.Actions, jwtauth.WildcardAction)
		pushAllowed := false
		if pushRequested {
			pushAllowed = h.policy.AuthorizeRepositoryAccess(
				r, principal, repositoryAccessItem(grant.Name, repositoryPushAction), allRequested,
			) == nil
		}
		pullContext := repositoryPolicyContext(allRequested, grant.Name, pushAllowed)
		for _, action := range grant.Actions {
			if action == jwtauth.WildcardAction {
				pullErr := h.policy.AuthorizeRepositoryAccess(r, principal, repositoryAccessItem(grant.Name, repositoryPullAction), pullContext)
				if pullErr == nil {
					allowedAction := repositoryPullAction
					if pushAllowed {
						allowedAction = jwtauth.WildcardAction
					}
					allowed.Actions = append(allowed.Actions, allowedAction)
				}
				continue
			}
			if action == repositoryPushAction {
				if pushAllowed {
					allowed.Actions = append(allowed.Actions, action)
				}
				continue
			}
			if err := h.policy.AuthorizeRepositoryAccess(r, principal, repositoryAccessItem(grant.Name, action), pullContext); err == nil {
				allowed.Actions = append(allowed.Actions, action)
			}
		}
		if len(allowed.Actions) > 0 {
			authorized = append(authorized, allowed)
		}
	}
	return authorized
}

func repositoryPolicyContext(requested []distauth.Access, name string, pushAllowed bool) []distauth.Access {
	context := make([]distauth.Access, 0, len(requested))
	for _, item := range requested {
		if item.Type == repositoryResourceType && item.Name == name && item.Action == repositoryPushAction {
			continue
		}
		context = append(context, item)
	}
	if pushAllowed {
		context = append(context, repositoryAccessItem(name, repositoryPushAction))
	}
	return context
}

func repositoryAccessItem(name, action string) distauth.Access {
	return distauth.Access{
		Resource: distauth.Resource{Type: repositoryResourceType, Name: name}, Action: action,
	}
}

func mergeAccess(access []jwtauth.ResourceActions) []jwtauth.ResourceActions {
	merged := make([]jwtauth.ResourceActions, 0, len(access))
	indices := make(map[string]int, len(access))
	for _, grant := range access {
		key := grant.Type + "\x00" + grant.Name
		if i, found := indices[key]; found {
			for _, action := range grant.Actions {
				if !slices.Contains(merged[i].Actions, action) {
					merged[i].Actions = append(merged[i].Actions, action)
				}
			}
			continue
		}
		normalized := jwtauth.ResourceActions{Type: grant.Type, Name: grant.Name}
		for _, action := range grant.Actions {
			if !slices.Contains(normalized.Actions, action) {
				normalized.Actions = append(normalized.Actions, action)
			}
		}
		indices[key] = len(merged)
		merged = append(merged, normalized)
	}
	return merged
}
