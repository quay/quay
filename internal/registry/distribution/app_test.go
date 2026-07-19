package distribution

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/oci"
	registryhandler "github.com/quay/quay/internal/registry"
	registryauth "github.com/quay/quay/internal/registry/auth"
)

func TestNewRegistryRejectsNilBlobLocker(t *testing.T) {
	_, err := NewRegistry(t.Context(), &Config{})
	if err == nil {
		t.Fatal("expected missing blob locker to be rejected")
	}
	if !strings.Contains(err.Error(), "nil blob locker") {
		t.Fatalf("expected nil blob locker error, got %v", err)
	}
}

func TestRegistryBearerChallengeExchangeAndRetry(t *testing.T) {
	db, err := dbcore.Setup(t.Context(), filepath.Join(t.TempDir(), "quay.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	store, err := metastore.NewSQLiteStore(t.Context(), db)
	if err != nil {
		t.Fatal(err)
	}
	signer, verifier, err := registryauth.NewES256Pair(registryauth.ES256Config{
		Issuer: registryauth.Issuer, Audience: "registry.example.com:8443",
		MaxFresh: 10 * time.Minute, ClockSkew: 5 * time.Second,
	})
	if err != nil {
		t.Fatal(err)
	}
	controller, err := registryauth.NewController(registryauth.ControllerConfig{
		Realm: "https://registry.example.com:8443/v2/auth", Service: "registry.example.com:8443",
		LibraryNamespace: "library", Verifier: verifier,
	})
	if err != nil {
		t.Fatal(err)
	}
	tokenHandler, err := registryauth.NewHandler(&registryauth.HandlerConfig{
		Service: "registry.example.com:8443", LibraryNamespace: "library", AnonymousAccess: true,
		Lifetime: 5 * time.Minute, Signer: signer,
		ResolveGrants: func(_ context.Context, _ registryauth.Identity, scopes []registryauth.Scope) ([]registryauth.ResourceActions, error) {
			grants := make([]registryauth.ResourceActions, 0, len(scopes))
			for _, scope := range scopes {
				grants = append(grants, registryauth.ResourceActions{Type: scope.Type, Name: scope.Name, Actions: scope.Actions})
			}
			return grants, nil
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	registry, err := NewRegistry(t.Context(), &Config{
		StoragePath: filepath.Join(t.TempDir(), "storage"), ListenAddr: ":0", Store: store,
		BlobLocker: oci.NewBlobLockSet(), LibraryNamespace: "library", AccessController: controller,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer registry.Close()
	mux := http.NewServeMux()
	mux.Handle("/v2/auth", tokenHandler)
	mux.Handle("/", registry.Handler())

	challengeRequest := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/", http.NoBody)
	challengeResponse := httptest.NewRecorder()
	mux.ServeHTTP(challengeResponse, challengeRequest)
	if challengeResponse.Code != http.StatusUnauthorized {
		t.Fatalf("challenge status = %d, body = %s", challengeResponse.Code, challengeResponse.Body.String())
	}
	challenge := challengeResponse.Header().Get("WWW-Authenticate")
	if !strings.Contains(challenge, `Bearer realm="https://registry.example.com:8443/v2/auth",service="registry.example.com:8443"`) {
		t.Fatalf("challenge = %q", challenge)
	}

	directBasic := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/", http.NoBody)
	directBasic.SetBasicAuth("user", "password")
	directBasicResponse := httptest.NewRecorder()
	mux.ServeHTTP(directBasicResponse, directBasic)
	if directBasicResponse.Code != http.StatusUnauthorized || strings.HasPrefix(directBasicResponse.Header().Get("WWW-Authenticate"), "Basic") {
		t.Fatalf("direct Basic response = %d, challenge = %q", directBasicResponse.Code, directBasicResponse.Header().Get("WWW-Authenticate"))
	}

	exchangeURL := "/v2/auth?service=" + url.QueryEscape("registry.example.com:8443") +
		"&scope=" + url.QueryEscape("repository:public/repo:pull")
	exchangeRequest := httptest.NewRequestWithContext(t.Context(), http.MethodGet, exchangeURL, http.NoBody)
	exchangeResponse := httptest.NewRecorder()
	mux.ServeHTTP(exchangeResponse, exchangeRequest)
	if exchangeResponse.Code != http.StatusOK {
		t.Fatalf("exchange status = %d, body = %s", exchangeResponse.Code, exchangeResponse.Body.String())
	}
	var tokenBody struct {
		Token string `json:"token"`
	}
	if err := json.NewDecoder(exchangeResponse.Body).Decode(&tokenBody); err != nil {
		t.Fatal(err)
	}

	retryRequest := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/", http.NoBody)
	retryRequest.Header.Set("Authorization", "Bearer "+tokenBody.Token)
	retryResponse := httptest.NewRecorder()
	mux.ServeHTTP(retryResponse, retryRequest)
	if retryResponse.Code != http.StatusOK {
		t.Fatalf("retry status = %d, body = %s", retryResponse.Code, retryResponse.Body.String())
	}

	if _, err := store.EnsureRepository(t.Context(), oci.RepositoryName{Namespace: "public", Name: "repo"}); err != nil {
		t.Fatal(err)
	}
	referrers := registryhandler.NewReferrersHandler(store, controller, &registryhandler.ReferrersConfig{
		LibraryNamespace: "library", LibrarySupport: true,
	})
	referrersRequest := httptest.NewRequestWithContext(t.Context(), http.MethodGet,
		"/v2/public/repo/referrers/"+digest.FromString("subject").String(), http.NoBody)
	referrersRequest.Header.Set("Authorization", "Bearer "+tokenBody.Token)
	referrersResponse := httptest.NewRecorder()
	referrers.ServeHTTP(referrersResponse, referrersRequest)
	if referrersResponse.Code != http.StatusOK {
		t.Fatalf("referrers status = %d, body = %s", referrersResponse.Code, referrersResponse.Body.String())
	}
}
