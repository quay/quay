package auth

import (
	"bytes"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/big"
	"time"
)

const (
	es256Algorithm       = "ES256"
	algorithmHeader      = "alg"
	keyIDHeader          = "kid"
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
	key   *ecdsa.PrivateKey
	keyID string
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
	keyID := rfc7638Thumbprint(&privateKey.PublicKey)
	if keyID == "" {
		return nil, nil, fmt.Errorf("generate ES256 key ID")
	}
	publicKey := privateKey.PublicKey

	return &es256Signer{key: privateKey, keyID: keyID}, &es256Verifier{
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
	if s == nil || s.key == nil || claims == nil {
		return "", fmt.Errorf("invalid signer or claims")
	}
	header, err := json.Marshal(map[string]string{algorithmHeader: es256Algorithm, keyIDHeader: s.keyID})
	if err != nil {
		return "", fmt.Errorf("marshal registry token header: %w", err)
	}
	payload, err := json.Marshal(claims)
	if err != nil {
		return "", fmt.Errorf("marshal registry claims: %w", err)
	}
	encodedHeader := base64.RawURLEncoding.EncodeToString(header)
	encodedPayload := base64.RawURLEncoding.EncodeToString(payload)
	signingInput := encodedHeader + "." + encodedPayload
	digest := sha256.Sum256([]byte(signingInput))
	r, signatureS, err := ecdsa.Sign(rand.Reader, s.key, digest[:])
	if err != nil {
		return "", fmt.Errorf("sign registry claims: %w", err)
	}
	coordinateSize := (s.key.Curve.Params().BitSize + 7) / 8
	signature := make([]byte, coordinateSize*2)
	r.FillBytes(signature[:coordinateSize])
	signatureS.FillBytes(signature[coordinateSize:])
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(signature), nil
}

func (v *es256Verifier) KeyID() string { return v.keyID }

func (v *es256Verifier) Verify(raw string) (*Claims, error) {
	payload, ok := v.verifySignedPayload(raw)
	if !ok {
		return nil, ErrInvalidToken
	}
	claims, ok := decodeClaims(payload)
	if !ok || !validAccess(claims.Access) || !v.validClaims(claims) {
		return nil, ErrInvalidToken
	}
	return claims, nil
}

func (v *es256Verifier) verifySignedPayload(raw string) ([]byte, bool) {
	if v == nil || v.key == nil || !validProtectedHeader(raw, v.keyID) {
		return nil, false
	}
	parts := splitCompactToken(raw)
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, false
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[2])
	coordinateSize := (v.key.Curve.Params().BitSize + 7) / 8
	if err != nil || len(signature) != coordinateSize*2 {
		return nil, false
	}
	digest := sha256.Sum256([]byte(parts[0] + "." + parts[1]))
	r := new(big.Int).SetBytes(signature[:coordinateSize])
	signatureS := new(big.Int).SetBytes(signature[coordinateSize:])
	if !ecdsa.Verify(v.key, digest[:], r, signatureS) {
		return nil, false
	}
	return payload, true
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

func validProtectedHeader(raw, expectedKeyID string) bool {
	parts := splitCompactToken(raw)
	if parts == nil {
		return false
	}
	headerBytes, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return false
	}
	var header map[string]json.RawMessage
	if err := json.Unmarshal(headerBytes, &header); err != nil {
		return false
	}
	var algorithm, keyID string
	if err := json.Unmarshal(header[algorithmHeader], &algorithm); err != nil || algorithm != es256Algorithm {
		return false
	}
	if err := json.Unmarshal(header[keyIDHeader], &keyID); err != nil || keyID != expectedKeyID {
		return false
	}
	for _, attackerSelectable := range []string{"jwk", "x5c", "x5u", "jku", "crit"} {
		if _, ok := header[attackerSelectable]; ok {
			return false
		}
	}
	return true
}

func splitCompactToken(raw string) []string {
	parts := make([]string, 0, 3)
	start := 0
	for i := 0; i < len(raw); i++ {
		if raw[i] != '.' {
			continue
		}
		parts = append(parts, raw[start:i])
		start = i + 1
	}
	parts = append(parts, raw[start:])
	if len(parts) != 3 || parts[0] == "" || parts[1] == "" || parts[2] == "" {
		return nil
	}
	return parts
}

func rfc7638Thumbprint(key *ecdsa.PublicKey) string {
	if key == nil || key.Curve != elliptic.P256() || key.X == nil || key.Y == nil {
		return ""
	}
	coordinateSize := (key.Curve.Params().BitSize + 7) / 8
	x := key.X.FillBytes(make([]byte, coordinateSize))
	y := key.Y.FillBytes(make([]byte, coordinateSize))
	canonical := fmt.Sprintf(`{"crv":"P-256","kty":"EC","x":%q,"y":%q}`,
		base64.RawURLEncoding.EncodeToString(x), base64.RawURLEncoding.EncodeToString(y))
	digest := sha256.Sum256([]byte(canonical))
	return base64.RawURLEncoding.EncodeToString(digest[:])
}
