package jwtauth

import (
	"crypto/rand"
	"crypto/rsa"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/go-jose/go-jose/v4"
	"github.com/go-jose/go-jose/v4/jwt"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestIssueAndAuthorize(t *testing.T) {
	now := time.Date(2026, 7, 20, 12, 0, 0, 0, time.UTC)
	service, _ := newTestService(t, now)
	access := []ResourceActions{{Type: RepositoryType, Name: "acme/widget", Actions: []string{PullAction, PushAction}}}

	raw, expires, err := service.Issue("acme+builder", access)
	require.NoError(t, err)
	assert.Equal(t, now.Add(time.Hour), expires)

	claims, err := service.Authorize(raw, []ResourceActions{{
		Type: RepositoryType, Name: "acme/widget", Actions: []string{PullAction},
	}})
	require.NoError(t, err)
	assert.Equal(t, DefaultIssuer, claims.Issuer)
	assert.Equal(t, "acme+builder", claims.Subject)
	assert.Equal(t, jwt.Audience{"registry.example.com:8443"}, claims.Audience)
	assert.NotEmpty(t, claims.ID)
	assert.Equal(t, access, claims.Access)

	_, err = service.Authorize(raw, []ResourceActions{{
		Type: RepositoryType, Name: "other/widget", Actions: []string{PullAction},
	}})
	assert.ErrorIs(t, err, ErrInsufficientScope)
}

func TestWildcardAndDeleteAuthorization(t *testing.T) {
	service, _ := newTestService(t, time.Now().UTC())
	raw, _, err := service.Issue("admin", []ResourceActions{{
		Type: RepositoryType, Name: "acme/widget", Actions: []string{WildcardAction},
	}})
	require.NoError(t, err)

	for _, action := range []string{PullAction, PushAction, "delete"} {
		_, err := service.Authorize(raw, []ResourceActions{{
			Type: RepositoryType, Name: "acme/widget", Actions: []string{action},
		}})
		assert.NoError(t, err, action)
	}
}

func TestValidateRejectsInvalidTokens(t *testing.T) {
	now := time.Date(2026, 7, 20, 12, 0, 0, 0, time.UTC)
	service, key := newTestService(t, now)
	kid := service.KeyID()
	validClaims := map[string]any{
		"iss": DefaultIssuer, "sub": "user", "aud": "registry.example.com:8443",
		"iat": now.Unix(), "nbf": now.Unix(), "exp": now.Add(time.Hour).Unix(), "jti": "test-id",
		"access": []ResourceActions{{Type: RepositoryType, Name: "acme/widget", Actions: []string{PullAction}}},
	}

	tests := []struct {
		name   string
		claims func() map[string]any
		kid    string
	}{
		{name: "wrong issuer", claims: changedClaims(validClaims, "iss", "other"), kid: kid},
		{name: "wrong audience", claims: changedClaims(validClaims, "aud", "other.example.com"), kid: kid},
		{name: "multiple audiences", claims: changedClaims(validClaims, "aud", []string{"registry.example.com:8443", "other"}), kid: kid},
		{name: "expired", claims: changedClaims(validClaims, "exp", now.Add(-time.Minute).Unix()), kid: kid},
		{name: "not before future", claims: changedClaims(validClaims, "nbf", now.Add(time.Minute).Unix()), kid: kid},
		{name: "issued at future", claims: changedClaims(validClaims, "iat", now.Add(time.Minute).Unix()), kid: kid},
		{name: "excessive age", claims: changedClaims(validClaims, "iat", now.Add(-2*time.Hour).Unix()), kid: kid},
		{name: "missing subject", claims: deletedClaim(validClaims, "sub"), kid: kid},
		{name: "missing expiration", claims: deletedClaim(validClaims, "exp"), kid: kid},
		{name: "missing not before", claims: deletedClaim(validClaims, "nbf"), kid: kid},
		{name: "missing issued at", claims: deletedClaim(validClaims, "iat"), kid: kid},
		{name: "missing access", claims: deletedClaim(validClaims, "access"), kid: kid},
		{name: "invalid resource type", claims: changedClaims(validClaims, "access", []ResourceActions{{Type: "registry", Name: "catalog", Actions: []string{WildcardAction}}}), kid: kid},
		{name: "invalid action", claims: changedClaims(validClaims, "access", []ResourceActions{{Type: RepositoryType, Name: "acme/widget", Actions: []string{"delete"}}}), kid: kid},
		{name: "unknown key id", claims: func() map[string]any { return cloneClaims(validClaims) }, kid: "unknown"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			raw := signTestClaims(t, key, tt.kid, tt.claims())
			_, err := service.Validate(raw)
			assert.ErrorIs(t, err, ErrInvalidToken)
		})
	}

	otherService, _ := newTestService(t, now)
	wrongSignature, _, err := otherService.Issue("user", validClaims["access"].([]ResourceActions))
	require.NoError(t, err)
	_, err = service.Validate(wrongSignature)
	assert.ErrorIs(t, err, ErrInvalidToken)

	validRaw := signTestClaims(t, key, kid, cloneClaims(validClaims))
	parts := strings.Split(validRaw, ".")
	require.Len(t, parts, 3)
	if parts[2][0] == 'A' {
		parts[2] = "B" + parts[2][1:]
	} else {
		parts[2] = "A" + parts[2][1:]
	}
	tampered := strings.Join(parts, ".")
	_, err = service.Validate(tampered)
	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestValidateAcceptsSourceCompatibleClaims(t *testing.T) {
	now := time.Date(2026, 7, 20, 12, 0, 0, 0, time.UTC)
	service, key := newTestService(t, now)
	claims := map[string]any{
		"iss": DefaultIssuer, "sub": AnonymousSubject, "aud": "registry.example.com:8443",
		"iat": now.Unix(), "nbf": now.Unix(), "exp": now.Add(time.Hour).Unix(),
		"access": []ResourceActions{
			{Type: RepositoryType, Name: "acme/private", Actions: []string{}},
			{Type: RepositoryType, Name: "public/publicrepo", Actions: []string{PullAction}},
		},
		"context": map[string]any{"kind": "anonymous"},
	}
	raw := signTestClaims(t, key, service.KeyID(), claims)

	validated, err := service.Validate(raw)

	require.NoError(t, err)
	assert.Empty(t, validated.ID)
	assert.Len(t, validated.Access, 2)
}

func TestChallengeValuePreservesHostnamePort(t *testing.T) {
	access := []ResourceActions{{Type: RepositoryType, Name: "acme/widget", Actions: []string{PullAction, PushAction}}}
	assert.Equal(t,
		`Bearer realm="https://registry.example.com:8443/v2/auth",service="registry.example.com:8443",scope="repository:acme/widget:pull,push"`,
		ChallengeValue("https://registry.example.com:8443/v2/auth", "registry.example.com:8443", access, ErrMissingToken),
	)
	assert.Contains(t, ChallengeValue("realm", "service", access, ErrInvalidToken), `error="invalid_token"`)
	assert.Contains(t, ChallengeValue("realm", "service", access, ErrInsufficientScope), `error="insufficient_scope"`)
}

func newTestService(t *testing.T, now time.Time) (*Service, *rsa.PrivateKey) {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	service, err := New(key, Config{Audience: "registry.example.com:8443", Now: func() time.Time { return now }})
	require.NoError(t, err)
	return service, key
}

func signTestClaims(t *testing.T, key *rsa.PrivateKey, kid string, claims map[string]any) string {
	t.Helper()
	signer, err := jose.NewSigner(
		jose.SigningKey{Algorithm: jose.RS256, Key: key},
		(&jose.SignerOptions{}).WithType("JWT").WithHeader(jose.HeaderKey("kid"), kid),
	)
	require.NoError(t, err)
	raw, err := jwt.Signed(signer).Claims(claims).Serialize()
	require.NoError(t, err)
	return raw
}

func cloneClaims(source map[string]any) map[string]any {
	result := make(map[string]any, len(source))
	for key, value := range source {
		result[key] = value
	}
	return result
}

func changedClaims(source map[string]any, key string, value any) func() map[string]any {
	return func() map[string]any {
		result := cloneClaims(source)
		result[key] = value
		return result
	}
}

func deletedClaim(source map[string]any, key string) func() map[string]any {
	return func() map[string]any {
		result := cloneClaims(source)
		delete(result, key)
		return result
	}
}

func TestErrorSentinelsRemainDistinct(t *testing.T) {
	assert.False(t, errors.Is(ErrInvalidToken, ErrInsufficientScope))
}
