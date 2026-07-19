package auth

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	distauth "github.com/distribution/distribution/v3/registry/auth"
)

func newTestController(t *testing.T, access []ResourceActions) (*Controller, string) {
	t.Helper()
	signer, verifier := newTestPair(t)
	claims := validTestClaims()
	claims.Access = access
	raw, err := signer.Sign(claims)
	if err != nil {
		t.Fatal(err)
	}
	controller, err := NewController(ControllerConfig{
		Realm: "https://registry.example.com:8443/v2/auth", Service: "registry.example.com:8443",
		LibraryNamespace: "library", Verifier: verifier,
	})
	if err != nil {
		t.Fatal(err)
	}
	return controller, raw
}

func repositoryAccess(name, action string) distauth.Access {
	return distauth.Access{Resource: distauth.Resource{Type: "repository", Name: name}, Action: action}
}

func TestControllerChallengesAreDeterministic(t *testing.T) {
	controller, _ := newTestController(t, []ResourceActions{})
	req := httptest.NewRequest(http.MethodGet, "/v2/acme/image/manifests/latest", http.NoBody)
	_, err := controller.Authorized(req,
		repositoryAccess("z/repo", "push"), repositoryAccess("a/repo", "pull"), repositoryAccess("z/repo", "pull"),
	)
	if err == nil {
		t.Fatal("expected challenge")
	}
	var challenge distauth.Challenge
	if !errors.As(err, &challenge) {
		t.Fatalf("error is %T, want auth.Challenge", err)
	}
	w := httptest.NewRecorder()
	challenge.SetHeaders(req, w)
	want := `Bearer realm="https://registry.example.com:8443/v2/auth",service="registry.example.com:8443",scope="repository:a/repo:pull repository:z/repo:pull,push"`
	if got := w.Header().Get("WWW-Authenticate"); got != want {
		t.Fatalf("challenge = %q, want %q", got, want)
	}

	req.SetBasicAuth("user", "password")
	_, err = controller.Authorized(req, repositoryAccess("a/repo", "pull"))
	challenge = nil
	if !errors.As(err, &challenge) {
		t.Fatalf("Basic request error is %T, want auth.Challenge", err)
	}
	w = httptest.NewRecorder()
	challenge.SetHeaders(req, w)
	if strings.Contains(w.Header().Get("WWW-Authenticate"), "error=") {
		t.Fatalf("mismatched auth scheme should be token-required: %s", w.Header().Get("WWW-Authenticate"))
	}
}

func TestControllerInvalidAndInsufficientScope(t *testing.T) {
	controller, raw := newTestController(t, []ResourceActions{{Type: "repository", Name: "acme/image", Actions: []string{"pull"}}})
	tests := []struct {
		name   string
		token  string
		access distauth.Access
		error  string
	}{
		{"malformed", "bad", repositoryAccess("acme/image", "pull"), `error="invalid_token"`},
		{"wrong action", raw, repositoryAccess("acme/image", "push"), `error="insufficient_scope"`},
		{"wrong resource", raw, repositoryAccess("acme/other", "pull"), `error="insufficient_scope"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/v2/", http.NoBody)
			req.Header.Set("Authorization", "Bearer "+tt.token)
			_, err := controller.Authorized(req, tt.access)
			var challenge distauth.Challenge
			if !errors.As(err, &challenge) {
				t.Fatalf("error = %v", err)
			}
			w := httptest.NewRecorder()
			challenge.SetHeaders(req, w)
			if !strings.Contains(w.Header().Get("WWW-Authenticate"), tt.error) {
				t.Fatalf("challenge = %q", w.Header().Get("WWW-Authenticate"))
			}
		})
	}
}

func TestControllerExactWildcardAndLibraryGrants(t *testing.T) {
	controller, raw := newTestController(t, []ResourceActions{
		{Type: "repository", Name: "acme/image", Actions: []string{"*"}},
		{Type: "repository", Name: "library/busybox", Actions: []string{"pull"}},
	})
	req := httptest.NewRequest(http.MethodGet, "/v2/", http.NoBody)
	req.Header.Set("Authorization", "Bearer "+raw)
	grant, err := controller.Authorized(req,
		repositoryAccess("acme/image", "delete"), repositoryAccess("busybox", "pull"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if grant.User.Name != "acme+robot" || len(grant.Resources) != 2 {
		t.Fatalf("grant = %#v", grant)
	}
}

func TestControllerConcurrentAuthorization(t *testing.T) {
	controller, raw := newTestController(t, []ResourceActions{{Type: "repository", Name: "acme/image", Actions: []string{"pull"}}})
	const workers = 64
	var wg sync.WaitGroup
	errs := make(chan error, workers)
	for range workers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			req := httptest.NewRequest(http.MethodGet, "/v2/acme/image/manifests/latest", http.NoBody)
			req.Header.Set("Authorization", "Bearer "+raw)
			_, err := controller.Authorized(req, repositoryAccess("acme/image", "pull"))
			errs <- err
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Fatal(err)
		}
	}
}
