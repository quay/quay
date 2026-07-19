package auth

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"net/url"
	"reflect"
	"strconv"
	"strings"
	"testing"
	"time"
)

type tokenResponse struct {
	Token       string `json:"token"`
	AccessToken string `json:"access_token"`
	ExpiresIn   int64  `json:"expires_in"`
	IssuedAt    string `json:"issued_at"`
}

func newTestHandler(t *testing.T, anonymous bool, authenticate AuthenticateFunc, resolver GrantResolver) (*Handler, TokenVerifier) {
	t.Helper()
	signer, verifier := newTestPair(t)
	handler, err := NewHandler(HandlerConfig{
		Service: "registry.example.com:8443", LibraryNamespace: "library", AnonymousAccess: anonymous,
		Lifetime: 5 * time.Minute, Signer: signer, Authenticate: authenticate, ResolveGrants: resolver,
		Now: func() time.Time { return testNow },
	})
	if err != nil {
		t.Fatal(err)
	}
	return handler, verifier
}

func TestHandlerIssuesDownscopedToken(t *testing.T) {
	var requested []Scope
	authenticate := func(_ context.Context, username, secret string) (Identity, bool) {
		if username != "user" || secret != "password" {
			return Identity{}, false
		}
		return Identity{Subject: username, Principal: int64(42)}, true
	}
	resolver := func(_ context.Context, identity Identity, scopes []Scope) ([]ResourceActions, error) {
		if identity.Principal != int64(42) {
			t.Fatalf("principal = %#v", identity.Principal)
		}
		requested = scopes
		return []ResourceActions{{Type: "repository", Name: "acme/image", Actions: []string{"pull"}}}, nil
	}
	handler, verifier := newTestHandler(t, false, authenticate, resolver)
	query := url.Values{
		"service":       {"registry.example.com:8443"},
		"scope":         {"repository:acme/image:pull,push", "repository:acme/image:pull"},
		"offline_token": {"true"},
	}
	req := httptest.NewRequest(http.MethodGet, "/v2/auth?"+query.Encode(), http.NoBody)
	req.SetBasicAuth("user", "password")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", w.Code, w.Body.String())
	}
	if w.Header().Get("Cache-Control") != "no-store" || w.Header().Get("Pragma") != "no-cache" {
		t.Fatalf("cache headers = %#v", w.Header())
	}
	wantScopes := []Scope{{Type: "repository", Name: "acme/image", Actions: []string{"pull", "push"}}}
	if !reflect.DeepEqual(requested, wantScopes) {
		t.Fatalf("scopes = %#v, want %#v", requested, wantScopes)
	}
	var response tokenResponse
	if err := json.NewDecoder(w.Body).Decode(&response); err != nil {
		t.Fatal(err)
	}
	if response.Token == "" || response.Token != response.AccessToken || response.ExpiresIn != 300 || response.IssuedAt != testNow.Format(time.RFC3339) {
		t.Fatalf("response = %#v", response)
	}
	claims, err := verifier.Verify(response.Token)
	if err != nil {
		t.Fatal(err)
	}
	if claims.Subject != "user" || !reflect.DeepEqual(claims.Access[0].Actions, []string{"pull"}) {
		t.Fatalf("claims = %#v", claims)
	}
}

func TestHandlerInvalidCredentialsNeverBecomeAnonymous(t *testing.T) {
	authenticate := func(context.Context, string, string) (Identity, bool) { return Identity{}, false }
	resolverCalled := false
	resolver := func(context.Context, Identity, []Scope) ([]ResourceActions, error) {
		resolverCalled = true
		return nil, nil
	}
	handler, _ := newTestHandler(t, true, authenticate, resolver)
	req := httptest.NewRequest(http.MethodGet, "/v2/auth?service=registry.example.com%3A8443&scope=repository%3Apublic%2Frepo%3Apull", http.NoBody)
	req.SetBasicAuth("user", "wrong")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized || resolverCalled {
		t.Fatalf("status = %d, resolverCalled = %v", w.Code, resolverCalled)
	}
}

func TestHandlerAnonymousEmptyAndPublicScopes(t *testing.T) {
	resolver := func(_ context.Context, identity Identity, scopes []Scope) ([]ResourceActions, error) {
		if !identity.Anonymous || identity.Subject != AnonymousSubject {
			t.Fatalf("identity = %#v", identity)
		}
		access := make([]ResourceActions, 0, len(scopes))
		for _, scope := range scopes {
			actions := []string{}
			if scope.Name == "public/repo" {
				actions = []string{"pull"}
			}
			access = append(access, ResourceActions{Type: scope.Type, Name: scope.Name, Actions: actions})
		}
		return access, nil
	}
	handler, verifier := newTestHandler(t, true, nil, resolver)
	for _, path := range []string{
		"/v2/auth?service=registry.example.com%3A8443",
		"/v2/auth?service=registry.example.com%3A8443&scope=repository%3Apublic%2Frepo%3Apull",
		"/v2/auth?service=registry.example.com%3A8443&scope=repository%3Aprivate%2Frepo%3Apull",
	} {
		req := httptest.NewRequest(http.MethodGet, path, http.NoBody)
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, req)
		if w.Code != http.StatusOK {
			t.Fatalf("%s status = %d", path, w.Code)
		}
		var response tokenResponse
		_ = json.NewDecoder(w.Body).Decode(&response)
		claims, err := verifier.Verify(response.Token)
		if err != nil {
			t.Fatal(err)
		}
		if claims.Subject != AnonymousSubject {
			t.Fatalf("subject = %q", claims.Subject)
		}
	}
}

func TestHandlerRejectsProtocolErrors(t *testing.T) {
	handler, _ := newTestHandler(t, false,
		func(context.Context, string, string) (Identity, bool) { return Identity{Subject: "user"}, true },
		func(context.Context, Identity, []Scope) ([]ResourceActions, error) { return []ResourceActions{}, nil },
	)
	tests := []struct {
		name, method, path string
		status             int
	}{
		{"method", http.MethodPost, "/v2/auth?service=registry.example.com%3A8443", http.StatusMethodNotAllowed},
		{"missing service", http.MethodGet, "/v2/auth", http.StatusBadRequest},
		{"wrong service", http.MethodGet, "/v2/auth?service=attacker.example", http.StatusBadRequest},
		{"repeated service", http.MethodGet, "/v2/auth?service=registry.example.com%3A8443&service=registry.example.com%3A8443", http.StatusBadRequest},
		{"invalid scope", http.MethodGet, "/v2/auth?service=registry.example.com%3A8443&scope=repository%3Aacme%2Frepo%3Ascan", http.StatusBadRequest},
		{"missing credentials", http.MethodGet, "/v2/auth?service=registry.example.com%3A8443", http.StatusUnauthorized},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(tt.method, tt.path, http.NoBody)
			if tt.name != "missing credentials" {
				req.SetBasicAuth("user", "password")
			}
			w := httptest.NewRecorder()
			handler.ServeHTTP(w, req)
			if w.Code != tt.status {
				t.Fatalf("status = %d, want %d", w.Code, tt.status)
			}
			if w.Header().Get("Cache-Control") != "no-store" || w.Header().Get("Pragma") != "no-cache" {
				t.Fatal("missing no-cache headers")
			}
		})
	}
}

func TestHandlerRejectsExcessiveScopesBeforeResolution(t *testing.T) {
	resolverCalled := false
	handler, _ := newTestHandler(t, true, nil,
		func(context.Context, Identity, []Scope) ([]ResourceActions, error) {
			resolverCalled = true
			return nil, nil
		},
	)
	query := url.Values{"service": {"registry.example.com:8443"}}
	for i := 0; i <= maximumScopeCount; i++ {
		query.Add("scope", "repository:acme/repo"+strconv.Itoa(i)+":pull")
	}
	request := httptest.NewRequest(http.MethodGet, "/v2/auth?"+query.Encode(), http.NoBody)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusBadRequest || resolverCalled {
		t.Fatalf("status = %d, resolverCalled = %v", response.Code, resolverCalled)
	}
}

func TestHandlerRejectsOversizedQueryBeforeResolution(t *testing.T) {
	resolverCalled := false
	handler, _ := newTestHandler(t, true, nil,
		func(context.Context, Identity, []Scope) ([]ResourceActions, error) {
			resolverCalled = true
			return nil, nil
		},
	)
	path := "/v2/auth?service=registry.example.com%3A8443&padding=" + strings.Repeat("x", maximumTokenQueryBytes)
	request := httptest.NewRequest(http.MethodGet, path, http.NoBody)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusBadRequest || resolverCalled {
		t.Fatalf("status = %d, resolverCalled = %v", response.Code, resolverCalled)
	}
}

func TestHandlerResolverFailure(t *testing.T) {
	handler, _ := newTestHandler(t, true, nil,
		func(context.Context, Identity, []Scope) ([]ResourceActions, error) {
			return nil, errors.New("database failed")
		},
	)
	req := httptest.NewRequest(http.MethodGet, "/v2/auth?service=registry.example.com%3A8443", http.NoBody)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d", w.Code)
	}
}
