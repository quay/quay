package distribution

import (
	"context"
	"database/sql"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	distauth "github.com/distribution/distribution/v3/registry/auth"
	quayauth "github.com/quay/quay/internal/auth"
	_ "modernc.org/sqlite"
)

type authenticationVerifierStub struct{}

func (authenticationVerifierStub) Verify(_ context.Context, credentials quayauth.Credentials) quayauth.Result {
	return quayauth.Result{Username: credentials.Username, Presented: true}
}

func TestNewAuthenticationComposesRegistryTokenFlow(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	authentication, err := NewAuthentication(db, authenticationVerifierStub{}, &AuthenticationConfig{
		Scheme: "https", Service: "registry.example.com:8443", LibraryNamespace: "library",
		AnonymousAccess: true, MaxTokenFreshness: 10 * time.Minute,
	})
	if err != nil {
		t.Fatal(err)
	}
	if authentication.Controller == nil || authentication.TokenHandler == nil {
		t.Fatalf("authentication = %#v", authentication)
	}

	request := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/", http.NoBody)
	_, err = authentication.Controller.Authorized(request)
	var challenge distauth.Challenge
	if !errors.As(err, &challenge) {
		t.Fatalf("challenge error = %v", err)
	}
	response := httptest.NewRecorder()
	challenge.SetHeaders(request, response)
	if header := response.Header().Get("WWW-Authenticate"); !strings.Contains(header, `realm="https://registry.example.com:8443/v2/auth"`) ||
		!strings.Contains(header, `service="registry.example.com:8443"`) {
		t.Fatalf("WWW-Authenticate = %q", header)
	}
}

func TestNewAuthenticationRejectsMissingDependencies(t *testing.T) {
	if _, err := NewAuthentication(nil, authenticationVerifierStub{}, nil); err == nil {
		t.Fatal("expected nil config error")
	}
	if _, err := NewAuthentication(nil, nil, &AuthenticationConfig{}); err == nil {
		t.Fatal("expected nil verifier error")
	}
}
