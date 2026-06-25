package v1

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/quay/quay/internal/auth"
)

type staticAuthenticator struct{}

func (staticAuthenticator) Authenticate(*http.Request) auth.Result {
	return auth.Result{
		Principal:     auth.Principal{Username: "user", Kind: auth.PrincipalUser},
		Username:      "user",
		Presented:     true,
		Authenticated: true,
	}
}

type testModule struct{}

func (testModule) Register(router *Router) {
	router.Handle(http.MethodGet, MatchFunc(func(path string) (Params, bool) {
		if path != "/api/v1/test" {
			return nil, false
		}
		return Params{}, true
	}), func(w http.ResponseWriter, _ *http.Request, _ Params) {
		WriteJSON(w, http.StatusOK, map[string]bool{"success": true})
	})
}

func TestNewRegistersOnlyProvidedModules(t *testing.T) {
	emptyHandler, err := New(Config{Authenticator: staticAuthenticator{}})
	if err != nil {
		t.Fatalf("new empty api: %v", err)
	}
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/api/v1/test", http.NoBody)
	rec := httptest.NewRecorder()
	emptyHandler.ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("empty api status = %d, want 404", rec.Code)
	}

	moduleHandler, err := New(Config{Authenticator: staticAuthenticator{}}, testModule{})
	if err != nil {
		t.Fatalf("new api: %v", err)
	}
	rec = httptest.NewRecorder()
	moduleHandler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("module api status = %d, want 200", rec.Code)
	}
}

func TestRouterMethodNotAllowed(t *testing.T) {
	handler, err := New(Config{Authenticator: staticAuthenticator{}}, testModule{})
	if err != nil {
		t.Fatalf("new api: %v", err)
	}

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/test", http.NoBody)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("status = %d, want 405", rec.Code)
	}
	if got := rec.Header().Get("Allow"); got != http.MethodGet {
		t.Fatalf("Allow = %q, want GET", got)
	}
}
