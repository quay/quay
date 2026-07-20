package auth

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/go-jose/go-jose/v4"
	"github.com/go-jose/go-jose/v4/jwt"
)

var testNow = time.Date(2026, 7, 19, 12, 0, 0, 0, time.UTC)

func newTestPair(t *testing.T) (TokenSigner, TokenVerifier) {
	t.Helper()
	signer, verifier, err := NewES256Pair(ES256Config{
		Issuer: Issuer, Audience: "registry.example.com:8443", MaxFresh: 10 * time.Minute,
		ClockSkew: 5 * time.Second, Now: func() time.Time { return testNow },
	})
	if err != nil {
		t.Fatal(err)
	}
	return signer, verifier
}

func validTestClaims() *Claims {
	return &Claims{
		Issuer: Issuer, Subject: "acme+robot", Audience: "registry.example.com:8443",
		IssuedAt: testNow.Unix(), NotBefore: testNow.Unix(), Expiration: testNow.Add(5 * time.Minute).Unix(),
		JWTID: "test-jti", Access: []ResourceActions{{Type: "repository", Name: "acme/image", Actions: []string{"pull"}}},
	}
}

func TestES256SignVerifyAndRFC7638KeyID(t *testing.T) {
	signer, verifier := newTestPair(t)
	raw, err := signer.Sign(validTestClaims())
	if err != nil {
		t.Fatal(err)
	}
	claims, err := verifier.Verify(raw)
	if err != nil {
		t.Fatal(err)
	}
	if claims.Subject != "acme+robot" {
		t.Fatalf("subject = %q", claims.Subject)
	}

	concrete := signer.(*es256Signer)
	size := (concrete.key.Curve.Params().BitSize + 7) / 8
	canonical := fmt.Sprintf(`{"crv":"P-256","kty":"EC","x":%q,"y":%q}`,
		base64.RawURLEncoding.EncodeToString(concrete.key.X.FillBytes(make([]byte, size))),
		base64.RawURLEncoding.EncodeToString(concrete.key.Y.FillBytes(make([]byte, size))))
	digest := sha256.Sum256([]byte(canonical))
	wantKeyID := base64.RawURLEncoding.EncodeToString(digest[:])
	if signer.KeyID() != wantKeyID || verifier.KeyID() != wantKeyID {
		t.Fatalf("kid = %q, want RFC 7638 thumbprint %q", signer.KeyID(), wantKeyID)
	}

	parts := strings.Split(raw, ".")
	headerJSON, _ := base64.RawURLEncoding.DecodeString(parts[0])
	var header map[string]any
	if err := json.Unmarshal(headerJSON, &header); err != nil {
		t.Fatal(err)
	}
	if header["alg"] != "ES256" || header["kid"] != wantKeyID {
		t.Fatalf("header = %#v", header)
	}
	if len(header) != 2 {
		t.Fatalf("unexpected protected headers: %#v", header)
	}
}

func TestES256KeyIDsDifferAcrossProcessKeys(t *testing.T) {
	first, _ := newTestPair(t)
	second, _ := newTestPair(t)
	if first.KeyID() == second.KeyID() {
		t.Fatal("independent process keys must have distinct thumbprints")
	}
}

func TestVerifierRejectsWrongKeyAndMalformedAlgorithms(t *testing.T) {
	signer, verifier := newTestPair(t)
	_, otherVerifier := newTestPair(t)
	raw, err := signer.Sign(validTestClaims())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := otherVerifier.Verify(raw); err == nil {
		t.Fatal("expected token signed by old process key to fail")
	}

	malformed := []string{
		"not-a-token",
		compactUnsigned(t, map[string]any{"alg": "none", "kid": signer.KeyID()}, validTestClaims()),
		compactUnsigned(t, map[string]any{"alg": "RS256", "kid": signer.KeyID()}, validTestClaims()),
		compactUnsigned(t, map[string]any{"alg": "ES256"}, validTestClaims()),
		compactUnsigned(t, map[string]any{"alg": "ES256", "kid": "unknown"}, validTestClaims()),
		compactUnsigned(t, map[string]any{"alg": "ES256", "kid": signer.KeyID(), jsonWebKeyHeader: map[string]string{"kty": "EC"}}, validTestClaims()),
	}
	for _, token := range malformed {
		if _, err := verifier.Verify(token); err == nil {
			t.Fatalf("expected malformed token %q to fail", token)
		}
	}
}

func TestVerifierRejectsSignedAttackerSelectableHeaders(t *testing.T) {
	signer, verifier := newTestPair(t)
	concrete := signer.(*es256Signer)
	tests := map[string]any{
		jsonWebKeyHeader: jose.JSONWebKey{Key: &concrete.key.PublicKey},
		"x5c":            []string{},
		"x5u":            "https://attacker.example/cert.pem",
		"jku":            "https://attacker.example/jwks.json",
		"crit":           []string{},
	}
	for name, value := range tests {
		t.Run(name, func(t *testing.T) {
			raw := signTestClaims(t, concrete, validTestClaims(), map[jose.HeaderKey]any{
				jose.HeaderKey(name): value,
			})
			if _, err := verifier.Verify(raw); err == nil {
				t.Fatal("expected attacker-selectable header to fail")
			}
		})
	}
}

func TestVerifierRejectsUnknownClaims(t *testing.T) {
	signer, verifier := newTestPair(t)
	claims := struct {
		*Claims
		Unexpected bool `json:"unexpected"`
	}{Claims: validTestClaims(), Unexpected: true}
	raw := signTestClaims(t, signer.(*es256Signer), claims, nil)
	if _, err := verifier.Verify(raw); err == nil {
		t.Fatal("expected unknown claim to fail")
	}
}

func TestVerifierRejectsInvalidClaims(t *testing.T) {
	tests := map[string]func(*Claims){
		"issuer":        func(c *Claims) { c.Issuer = "other" },
		"audience":      func(c *Claims) { c.Audience = "other" },
		"subject":       func(c *Claims) { c.Subject = "" },
		"jti":           func(c *Claims) { c.JWTID = "" },
		"issued at":     func(c *Claims) { c.IssuedAt = 0 },
		"not before":    func(c *Claims) { c.NotBefore = 0 },
		"expiration":    func(c *Claims) { c.Expiration = 0 },
		"expired":       func(c *Claims) { c.Expiration = testNow.Add(-6 * time.Second).Unix() },
		"future issued": func(c *Claims) { c.IssuedAt = testNow.Add(6 * time.Second).Unix(); c.NotBefore = c.IssuedAt },
		"not yet valid": func(c *Claims) { c.NotBefore = testNow.Add(6 * time.Second).Unix() },
		"overlong":      func(c *Claims) { c.Expiration = testNow.Add(11 * time.Minute).Unix() },
		"stale": func(c *Claims) {
			c.IssuedAt = testNow.Add(-11 * time.Minute).Unix()
			c.NotBefore = c.IssuedAt
			c.Expiration = testNow.Add(time.Minute).Unix()
		},
		"missing access":  func(c *Claims) { c.Access = nil },
		"bad access type": func(c *Claims) { c.Access[0].Type = "" },
		"bad access name": func(c *Claims) { c.Access[0].Name = "" },
		"missing actions": func(c *Claims) { c.Access[0].Actions = nil },
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			signer, verifier := newTestPair(t)
			claims := validTestClaims()
			mutate(claims)
			raw, err := signer.Sign(claims)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := verifier.Verify(raw); err == nil {
				t.Fatal("expected invalid claims to fail")
			}
		})
	}
}

func compactUnsigned(t *testing.T, header, claims any) string {
	t.Helper()
	headerJSON, err := json.Marshal(header)
	if err != nil {
		t.Fatal(err)
	}
	claimsJSON, err := json.Marshal(claims)
	if err != nil {
		t.Fatal(err)
	}
	return base64.RawURLEncoding.EncodeToString(headerJSON) + "." +
		base64.RawURLEncoding.EncodeToString(claimsJSON) + "." + base64.RawURLEncoding.EncodeToString(make([]byte, 64))
}

func signTestClaims(t *testing.T, signer *es256Signer, claims any, headers map[jose.HeaderKey]any) string {
	t.Helper()
	options := &jose.SignerOptions{}
	options.WithHeader(jose.HeaderKey("kid"), signer.keyID)
	for name, value := range headers {
		options.WithHeader(name, value)
	}
	joseSigner, err := jose.NewSigner(jose.SigningKey{Algorithm: jose.ES256, Key: signer.key}, options)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := jwt.Signed(joseSigner).Claims(claims).Serialize()
	if err != nil {
		t.Fatal(err)
	}
	return raw
}
