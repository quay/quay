package auth

import (
	"bytes"
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/go-jose/go-jose/v4"
	"github.com/go-jose/go-jose/v4/jwt"
)

const (
	maximumClockSkew     = 5 * time.Second
	minimumTokenLifetime = 60 * time.Second
)

// ErrInvalidToken is returned for every malformed or invalid bearer token.
var ErrInvalidToken = errors.New("invalid registry bearer token")

// ES256Config configures an ephemeral ES256 signer/verifier pair.
type ES256Config struct {
	Issuer    string
	Audience  string
	MaxFresh  time.Duration
	ClockSkew time.Duration
	Now       func() time.Time
}

type es256Signer struct {
	key        *ecdsa.PrivateKey
	keyID      string
	joseSigner jose.Signer
}

type es256Verifier struct {
	key       *ecdsa.PublicKey
	keyID     string
	issuer    string
	audience  string
	maxFresh  time.Duration
	clockSkew time.Duration
	now       func() time.Time
}

// NewES256Pair generates a process-ephemeral P-256 key and returns a signer
// that owns the private key and a verifier that retains only the public key.
func NewES256Pair(cfg ES256Config) (TokenSigner, TokenVerifier, error) {
	if cfg.Issuer == "" || cfg.Audience == "" {
		return nil, nil, fmt.Errorf("issuer and audience must not be empty")
	}
	if cfg.MaxFresh < minimumTokenLifetime {
		return nil, nil, fmt.Errorf("maximum token freshness must be at least %s", minimumTokenLifetime)
	}
	if cfg.ClockSkew < 0 || cfg.ClockSkew > maximumClockSkew {
		return nil, nil, fmt.Errorf("clock skew must be between zero and %s", maximumClockSkew)
	}
	if cfg.Now == nil {
		cfg.Now = time.Now
	}

	privateKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return nil, nil, fmt.Errorf("generate ES256 key: %w", err)
	}
	thumbprint, err := (&jose.JSONWebKey{Key: &privateKey.PublicKey}).Thumbprint(crypto.SHA256)
	if err != nil {
		return nil, nil, fmt.Errorf("generate ES256 key ID: %w", err)
	}
	keyID := base64.RawURLEncoding.EncodeToString(thumbprint)
	if keyID == "" {
		return nil, nil, fmt.Errorf("generate ES256 key ID: empty thumbprint")
	}
	joseSigner, err := jose.NewSigner(jose.SigningKey{
		Algorithm: jose.ES256,
		Key: jose.JSONWebKey{
			Key:       privateKey,
			KeyID:     keyID,
			Algorithm: string(jose.ES256),
		},
	}, nil)
	if err != nil {
		return nil, nil, fmt.Errorf("create ES256 signer: %w", err)
	}
	publicKey := privateKey.PublicKey

	return &es256Signer{key: privateKey, keyID: keyID, joseSigner: joseSigner}, &es256Verifier{
		key:       &publicKey,
		keyID:     keyID,
		issuer:    cfg.Issuer,
		audience:  cfg.Audience,
		maxFresh:  cfg.MaxFresh,
		clockSkew: cfg.ClockSkew,
		now:       cfg.Now,
	}, nil
}

func (s *es256Signer) KeyID() string { return s.keyID }

func (s *es256Signer) Sign(claims *Claims) (string, error) {
	if s == nil || s.key == nil || s.joseSigner == nil || claims == nil {
		return "", fmt.Errorf("invalid signer or claims")
	}
	raw, err := jwt.Signed(s.joseSigner).Claims(claims).Serialize()
	if err != nil {
		return "", fmt.Errorf("sign registry claims: %w", err)
	}
	return raw, nil
}

func (v *es256Verifier) KeyID() string { return v.keyID }

func (v *es256Verifier) Verify(raw string) (*Claims, error) {
	if v == nil || v.key == nil {
		return nil, ErrInvalidToken
	}
	token, err := jwt.ParseSigned(raw, []jose.SignatureAlgorithm{jose.ES256})
	if err != nil || len(token.Headers) != 1 || !validProtectedHeader(raw, token.Headers[0], v.keyID) {
		return nil, ErrInvalidToken
	}
	var payload json.RawMessage
	if err := token.Claims(v.key, &payload); err != nil {
		return nil, ErrInvalidToken
	}
	claims, ok := decodeClaims(payload)
	if !ok || !validAccess(claims.Access) || !v.validClaims(claims) {
		return nil, ErrInvalidToken
	}
	return claims, nil
}

func decodeClaims(payload []byte) (*Claims, bool) {
	var claims Claims
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&claims); err != nil || claims.Access == nil {
		return nil, false
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		return nil, false
	}
	return &claims, true
}

func validAccess(access []ResourceActions) bool {
	for _, item := range access {
		if item.Type == "" || item.Name == "" || item.Actions == nil || !validAccessResource(item) || !validAccessActions(item) {
			return false
		}
	}
	return true
}

func validAccessResource(item ResourceActions) bool {
	switch item.Type {
	case repositoryResourceType:
		return validRepositoryName(item.Name)
	case registryResourceType:
		return validToken(item.Name)
	default:
		return false
	}
}

func validAccessActions(item ResourceActions) bool {
	for _, action := range item.Actions {
		if !validScopeAction(action) || item.Type == registryResourceType && action != wildcardAction {
			return false
		}
	}
	return true
}

func (v *es256Verifier) validClaims(claims *Claims) bool {
	if !v.validRequiredClaims(claims) {
		return false
	}
	return v.validClaimTimes(claims)
}

func (v *es256Verifier) validRequiredClaims(claims *Claims) bool {
	if claims.Issuer != v.issuer || claims.Audience != v.audience || claims.Subject == "" || claims.JWTID == "" {
		return false
	}
	if claims.IssuedAt <= 0 || claims.NotBefore <= 0 || claims.Expiration <= 0 {
		return false
	}
	return true
}

func (v *es256Verifier) validClaimTimes(claims *Claims) bool {
	now := v.now().UTC()
	issuedAt := time.Unix(claims.IssuedAt, 0)
	notBefore := time.Unix(claims.NotBefore, 0)
	expires := time.Unix(claims.Expiration, 0)
	if issuedAt.After(now.Add(v.clockSkew)) || now.Before(notBefore.Add(-v.clockSkew)) || now.After(expires.Add(v.clockSkew)) {
		return false
	}
	if expires.Before(issuedAt) || expires.Equal(issuedAt) || expires.Sub(issuedAt) > v.maxFresh {
		return false
	}
	if notBefore.Before(issuedAt.Add(-v.clockSkew)) || notBefore.After(issuedAt.Add(v.clockSkew)) {
		return false
	}
	return now.Sub(issuedAt) <= v.maxFresh+v.clockSkew
}

func validProtectedHeader(raw string, header jose.Header, expectedKeyID string) bool {
	if header.Algorithm != string(jose.ES256) || header.KeyID != expectedKeyID {
		return false
	}
	// go-jose intentionally hides the raw x5c field after parsing. Inspect the
	// protected object so even empty attacker-selectable key headers are rejected.
	encodedHeader, _, ok := strings.Cut(raw, ".")
	if !ok {
		return false
	}
	headerBytes, err := base64.RawURLEncoding.DecodeString(encodedHeader)
	if err != nil {
		return false
	}
	var protected map[string]json.RawMessage
	if err := json.Unmarshal(headerBytes, &protected); err != nil {
		return false
	}
	for _, attackerSelectable := range []string{"jwk", "x5c", "x5u", "jku", "crit"} {
		if _, ok := protected[attackerSelectable]; ok {
			return false
		}
	}
	return true
}
