package distribution

import (
	"crypto/rand"
	"crypto/rsa"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"

	distauth "github.com/distribution/distribution/v3/registry/auth"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/registry/jwtauth"
)

func TestTokenHandlerUserPullPushFlow(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	seedRobotPermission(t, db, "admin", "write")
	handler, service, _ := newBearerTestComponents(t, db, true)

	raw := requestToken(t, handler, "admin", "correct-password", "repository:acme/private:pull,push", http.StatusOK)
	claims, err := service.Authorize(raw, []jwtauth.ResourceActions{{
		Type: jwtauth.RepositoryType, Name: "acme/private", Actions: []string{jwtauth.PullAction, jwtauth.PushAction},
	}})
	require.NoError(t, err)
	assert.Equal(t, "admin", claims.Subject)
	assert.WithinDuration(t, time.Now().Add(time.Hour), claims.Expiry.Time(), 5*time.Second)
}

func TestTokenHandlerRobotCredentialsAndDownscoping(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	seedRobotPermission(t, db, "acme+reader", "read")
	handler, service, _ := newBearerTestComponents(t, db, true)

	raw := requestToken(t, handler, "acme+reader", "hello world", "repository:acme/private:pull,push", http.StatusOK)
	claims, err := service.Validate(raw)
	require.NoError(t, err)
	assert.Equal(t, "acme+reader", claims.Subject)
	assert.Equal(t, []jwtauth.ResourceActions{{
		Type: jwtauth.RepositoryType, Name: "acme/private", Actions: []string{jwtauth.PullAction},
	}}, claims.Access)

	_, err = service.Authorize(raw, []jwtauth.ResourceActions{{
		Type: jwtauth.RepositoryType, Name: "acme/private", Actions: []string{jwtauth.PushAction},
	}})
	assert.ErrorIs(t, err, jwtauth.ErrInsufficientScope)
}

func TestTokenHandlerWildcardDownscopesToPull(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	seedRobotPermission(t, db, "acme+reader", "read")
	handler, service, _ := newBearerTestComponents(t, db, true)

	raw := requestToken(t, handler, "acme+reader", "hello world", "repository:acme/private:*", http.StatusOK)
	claims, err := service.Validate(raw)

	require.NoError(t, err)
	assert.Equal(t, []jwtauth.ResourceActions{{
		Type: jwtauth.RepositoryType, Name: "acme/private", Actions: []string{jwtauth.PullAction},
	}}, claims.Access)
}

func TestTokenHandlerAnonymousAccess(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	handler, service, _ := newBearerTestComponents(t, db, true)

	publicRaw := requestToken(t, handler, "", "", "repository:public/publicrepo:pull", http.StatusOK)
	publicClaims, err := service.Validate(publicRaw)
	require.NoError(t, err)
	assert.Equal(t, jwtauth.AnonymousSubject, publicClaims.Subject)
	assert.Equal(t, []jwtauth.ResourceActions{{
		Type: jwtauth.RepositoryType, Name: "public/publicrepo", Actions: []string{jwtauth.PullAction},
	}}, publicClaims.Access)

	privateRaw := requestToken(t, handler, "", "", "repository:acme/private:pull", http.StatusOK)
	privateClaims, err := service.Validate(privateRaw)
	require.NoError(t, err)
	assert.Empty(t, privateClaims.Access)
}

func TestTokenHandlerRejectsAnonymousNoScopeRequest(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	handler, _, _ := newBearerTestComponents(t, db, true)

	requestToken(t, handler, "", "", "", http.StatusUnauthorized)
}

func TestTokenHandlerAuthenticatedNoScopeToken(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	handler, service, _ := newBearerTestComponents(t, db, true)

	raw := requestToken(t, handler, "admin", "correct-password", "", http.StatusOK)
	claims, err := service.Validate(raw)

	require.NoError(t, err)
	assert.Equal(t, "admin", claims.Subject)
	assert.Empty(t, claims.Access)
}

func TestTokenHandlerMergesRepeatedAndDuplicateScopes(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	seedRobotPermission(t, db, "admin", "write")
	handler, service, _ := newBearerTestComponents(t, db, true)
	query := url.Values{"service": []string{testTokenService}}
	query.Add("scope", "repository:acme/private:pull,pull")
	query.Add("scope", "repository:acme/private:push repository:acme/private:pull")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/auth?"+query.Encode(), http.NoBody)
	req.SetBasicAuth("admin", "correct-password")
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	require.Equal(t, http.StatusOK, w.Code, w.Body.String())
	raw := decodeTokenResponse(t, w)
	claims, err := service.Validate(raw)
	require.NoError(t, err)
	assert.Equal(t, []jwtauth.ResourceActions{{
		Type: jwtauth.RepositoryType, Name: "acme/private", Actions: []string{jwtauth.PullAction, jwtauth.PushAction},
	}}, claims.Access)
}

func TestTokenHandlerDoesNotGrantPullWhenMissingRepositoryPushIsDenied(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	handler, service, _ := newBearerTestComponents(t, db, true)

	raw := requestToken(t, handler, "", "", "repository:acme/future-private:pull,push", http.StatusOK)
	claims, err := service.Validate(raw)

	require.NoError(t, err)
	assert.Empty(t, claims.Access)
}

func TestTokenHandlerLimitsRequestedScopes(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	handler, _, _ := newBearerTestComponents(t, db, true)

	t.Run("count", func(t *testing.T) {
		query := url.Values{"service": []string{testTokenService}}
		for i := 0; i <= maxRequestedScopeCount; i++ {
			query.Add("scope", fmt.Sprintf("repository:public/repo-%d:pull", i))
		}
		req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/auth?"+query.Encode(), http.NoBody)
		w := httptest.NewRecorder()

		handler.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code, w.Body.String())
	})

	t.Run("bytes", func(t *testing.T) {
		query := url.Values{"service": []string{testTokenService}}
		query.Set("scope", "repository:public/"+strings.Repeat("a", maxRequestedScopeBytes)+":pull")
		req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/auth?"+query.Encode(), http.NoBody)
		w := httptest.NewRecorder()

		handler.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code, w.Body.String())
	})
}

func TestTokenHandlerRejectsInvalidRequests(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	handler, _, _ := newBearerTestComponents(t, db, true)

	tests := []struct {
		name, username, password, service, account, scope string
		status                                            int
	}{
		{name: "wrong password", username: "admin", password: "wrong", scope: "repository:public/publicrepo:pull", status: http.StatusUnauthorized},
		{name: "unknown user", username: "missing", password: "wrong", scope: "repository:public/publicrepo:pull", status: http.StatusUnauthorized},
		{name: "disabled user", username: "disabled", password: "correct-password", scope: "repository:public/publicrepo:pull", status: http.StatusUnauthorized},
		{name: "wrong service", service: "other.example.com", scope: "repository:public/publicrepo:pull", status: http.StatusBadRequest},
		{name: "account mismatch", username: "admin", password: "correct-password", account: "other", scope: "repository:public/publicrepo:pull", status: http.StatusUnauthorized},
		{name: "invalid type", scope: "registry:catalog:*", status: http.StatusBadRequest},
		{name: "invalid action", scope: "repository:public/publicrepo:delete", status: http.StatusBadRequest},
		{name: "malformed", scope: "repository:missing", status: http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			query := url.Values{"scope": []string{tt.scope}}
			if tt.service != "" {
				query.Set("service", tt.service)
			} else {
				query.Set("service", testTokenService)
			}
			if tt.account != "" {
				query.Set("account", tt.account)
			}
			req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/auth?"+query.Encode(), http.NoBody)
			if tt.username != "" {
				req.SetBasicAuth(tt.username, tt.password)
			}
			w := httptest.NewRecorder()
			handler.ServeHTTP(w, req)
			assert.Equal(t, tt.status, w.Code, w.Body.String())
			if tt.status == http.StatusUnauthorized {
				assert.Contains(t, w.Header().Get("WWW-Authenticate"), "Basic realm=")
			}
		})
	}
}

func TestBearerAccessControllerChallengeAndScope(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	seedRobotPermission(t, db, "admin", "write")
	handler, service, controller := newBearerTestComponents(t, db, false)
	access := repositoryAccess("acme/private", repositoryPullAction)

	missingReq := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/acme/private/manifests/latest", http.NoBody)
	_, err := controller.Authorized(missingReq, access)
	require.Error(t, err)
	var challenge distauth.Challenge
	require.ErrorAs(t, err, &challenge)
	w := httptest.NewRecorder()
	challenge.SetHeaders(missingReq, w)
	assert.Equal(t,
		`Bearer realm="https://registry.example.com:8443/v2/auth",service="registry.example.com:8443",scope="repository:acme/private:pull"`,
		w.Header().Get("WWW-Authenticate"),
	)

	pullToken := requestToken(t, handler, "admin", "correct-password", "repository:acme/private:pull", http.StatusOK)
	pushReq := httptest.NewRequestWithContext(t.Context(), http.MethodPut, "/v2/acme/private/manifests/latest", http.NoBody)
	pushReq.Header.Set("Authorization", "Bearer "+pullToken)
	_, err = controller.Authorized(pushReq, repositoryAccess("acme/private", repositoryPushAction))
	require.Error(t, err)
	require.ErrorAs(t, err, &challenge)
	w = httptest.NewRecorder()
	challenge.SetHeaders(pushReq, w)
	assert.Contains(t, w.Header().Get("WWW-Authenticate"), `error="insufficient_scope"`)

	claims, err := service.Validate(pullToken)
	require.NoError(t, err)
	assert.Equal(t, "admin", claims.Subject)
}

func TestBearerAccessControllerAllowsDirectAnonymousPublicPull(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	_, _, controller := newBearerTestComponents(t, db, true)
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/public/publicrepo/manifests/latest", http.NoBody)

	grant, err := controller.Authorized(req, repositoryAccess("public/publicrepo", repositoryPullAction))
	require.NoError(t, err)
	assert.Equal(t, "anonymous", grant.User.Name)
}

func TestBearerAccessControllerRejectsBasicCredentialsOnRegistryRequests(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	_, _, controller := newBearerTestComponents(t, db, false)
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/acme/private/manifests/latest", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	_, err := controller.Authorized(req, repositoryAccess("acme/private", repositoryPullAction))

	require.Error(t, err)
	var challenge distauth.Challenge
	require.ErrorAs(t, err, &challenge)
	w := httptest.NewRecorder()
	challenge.SetHeaders(req, w)
	assert.Equal(t,
		`Bearer realm="https://registry.example.com:8443/v2/auth",service="registry.example.com:8443",scope="repository:acme/private:pull"`,
		w.Header().Get("WWW-Authenticate"),
	)
}

func TestBearerAccessControllerRejectsMalformedAuthorizationHeaders(t *testing.T) {
	db := setupTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	_, _, controller := newBearerTestComponents(t, db, false)
	tests := []struct {
		name, authorization string
		wantErrorParam      string
	}{
		{name: "bearer without token", authorization: "Bearer"},
		{name: "empty bearer token", authorization: "Bearer    "},
		{name: "wrong scheme", authorization: "Token opaque"},
		{name: "invalid jwt", authorization: "Bearer not-a-jwt", wantErrorParam: `error="invalid_token"`},
		{name: "extra bearer fields", authorization: "Bearer token extra", wantErrorParam: `error="invalid_token"`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/acme/private/manifests/latest", http.NoBody)
			req.Header.Set("Authorization", tt.authorization)

			_, err := controller.Authorized(req, repositoryAccess("acme/private", repositoryPullAction))

			require.Error(t, err)
			var challenge distauth.Challenge
			require.ErrorAs(t, err, &challenge)
			w := httptest.NewRecorder()
			challenge.SetHeaders(req, w)
			value := w.Header().Get("WWW-Authenticate")
			assert.Contains(t, value, `Bearer realm="https://registry.example.com:8443/v2/auth"`)
			if tt.wantErrorParam == "" {
				assert.NotContains(t, value, "error=")
			} else {
				assert.Contains(t, value, tt.wantErrorParam)
			}
		})
	}
}

const testTokenService = "registry.example.com:8443"

func newBearerTestComponents(t *testing.T, db *sql.DB, anonymous bool) (*TokenHandler, *jwtauth.Service, *accessController) {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	service, err := jwtauth.New(key, jwtauth.Config{Audience: testTokenService})
	require.NoError(t, err)
	controller, err := newAccessController(map[string]interface{}{
		authOptionRealm:       "https://registry.example.com:8443/v2/auth",
		authOptionService:     testTokenService,
		authOptionJWTService:  service,
		"db":                  db,
		authOptionAnonAccess:  anonymous,
		authOptionDatabaseKey: "test1234",
		authOptionLastAccess:  true,
		authOptionLastAccessS: 0,
	})
	require.NoError(t, err)
	handler, err := newTokenHandler(
		controller.authenticator,
		controllerTokenPolicy{controller: controller},
		service,
		anonymous,
	)
	require.NoError(t, err)
	return handler, service, controller
}

func requestToken(t *testing.T, handler http.Handler, username, password, scope string, wantStatus int) string {
	t.Helper()
	query := url.Values{"service": []string{testTokenService}}
	if scope != "" {
		query.Add("scope", scope)
	}
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/auth?"+query.Encode(), http.NoBody)
	if username != "" {
		req.SetBasicAuth(username, password)
	}
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	require.Equal(t, wantStatus, w.Code, w.Body.String())
	if wantStatus != http.StatusOK {
		return ""
	}
	return decodeTokenResponse(t, w)
}

func decodeTokenResponse(t *testing.T, w *httptest.ResponseRecorder) string {
	t.Helper()
	var response struct {
		Token       string `json:"token"`
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
		IssuedAt    string `json:"issued_at"`
	}
	require.NoError(t, json.NewDecoder(w.Body).Decode(&response))
	assert.NotEmpty(t, response.Token)
	assert.Equal(t, response.Token, response.AccessToken)
	assert.Equal(t, int64(3600), response.ExpiresIn)
	assert.NotEmpty(t, response.IssuedAt)
	assert.Equal(t, "no-store", w.Header().Get("Cache-Control"))
	return response.Token
}
