// Package jwtauth implements the Docker Registry v2 JWT token profile.
package jwtauth

import (
	"crypto/rand"
	"crypto/rsa"
	"encoding/hex"
	"errors"
	"fmt"
	"slices"
	"strings"
	"time"

	"github.com/go-jose/go-jose/v4"
	"github.com/go-jose/go-jose/v4/jwt"
)

const (
	// DefaultIssuer identifies tokens issued by the registry service.
	DefaultIssuer = "quay"
	// AnonymousSubject identifies an unauthenticated token subject.
	AnonymousSubject = "(anonymous)"
	// RepositoryType is the Docker Registry repository resource type.
	RepositoryType = "repository"
	// PullAction grants repository read access.
	PullAction = "pull"
	// PushAction grants repository write and delete access.
	PushAction = "push"
	// WildcardAction grants every supported repository action.
	WildcardAction = "*"
	deleteAction   = "delete"

	// DefaultLifetime is the validity period for newly issued tokens.
	DefaultLifetime = time.Hour
	// DefaultLeeway is the allowed clock skew during validation.
	DefaultLeeway = 30 * time.Second
	// DefaultMaxAge bounds the lifetime encoded in a token.
	DefaultMaxAge = 3660 * time.Second
)

var (
	// ErrMissingToken indicates that a request did not contain a Bearer token.
	ErrMissingToken = errors.New("bearer token required")
	// ErrInvalidToken indicates that a Bearer token failed validation.
	ErrInvalidToken = errors.New("invalid bearer token")
	// ErrInsufficientScope indicates that a valid token lacks required access.
	ErrInsufficientScope = errors.New("insufficient bearer token scope")
)

// ResourceActions is one Docker Registry access grant.
type ResourceActions struct {
	Type    string   `json:"type"`
	Name    string   `json:"name"`
	Actions []string `json:"actions"`
}

// Claims is the JWT claim set used by Docker and OCI clients.
type Claims struct {
	jwt.Claims
	Access []ResourceActions `json:"access"`
}

// Config controls token identity and time validation.
type Config struct {
	Issuer   string
	Audience string
	Lifetime time.Duration
	Leeway   time.Duration
	MaxAge   time.Duration
	Now      func() time.Time
}

// Service signs and validates registry JWTs with one persisted RSA key.
type Service struct {
	issuer    string
	audience  string
	lifetime  time.Duration
	leeway    time.Duration
	maxAge    time.Duration
	now       func() time.Time
	kid       string
	publicKey *rsa.PublicKey
	signer    jose.Signer
}

// LoadOrCreate loads the native v3 key (or creates it for a fresh install)
// and returns the concrete JWT service used by the registry.
func LoadOrCreate(dataDir string, cfg Config) (*Service, error) {
	key, err := LoadOrCreatePrivateKey(dataDir)
	if err != nil {
		return nil, err
	}
	return New(key, cfg)
}

// New creates a registry JWT service.
func New(key *rsa.PrivateKey, cfg Config) (*Service, error) {
	if key == nil {
		return nil, fmt.Errorf("nil registry JWT signing key")
	}
	if cfg.Issuer == "" {
		cfg.Issuer = DefaultIssuer
	}
	if cfg.Audience == "" {
		return nil, fmt.Errorf("registry JWT audience is required")
	}
	if cfg.Lifetime == 0 {
		cfg.Lifetime = DefaultLifetime
	}
	if cfg.Leeway == 0 {
		cfg.Leeway = DefaultLeeway
	}
	if cfg.MaxAge == 0 {
		cfg.MaxAge = DefaultMaxAge
	}
	if cfg.Lifetime <= 0 || cfg.MaxAge <= 0 || cfg.Lifetime > cfg.MaxAge {
		return nil, fmt.Errorf("invalid registry JWT lifetime configuration")
	}
	if cfg.Now == nil {
		cfg.Now = time.Now
	}

	kid, err := KeyID(&key.PublicKey)
	if err != nil {
		return nil, err
	}
	signer, err := jose.NewSigner(
		jose.SigningKey{Algorithm: jose.RS256, Key: key},
		(&jose.SignerOptions{}).WithType("JWT").WithHeader(jose.HeaderKey("kid"), kid),
	)
	if err != nil {
		return nil, fmt.Errorf("create registry JWT signer: %w", err)
	}

	return &Service{
		issuer: cfg.Issuer, audience: cfg.Audience, lifetime: cfg.Lifetime,
		leeway: cfg.Leeway, maxAge: cfg.MaxAge, now: cfg.Now, kid: kid,
		publicKey: &key.PublicKey, signer: signer,
	}, nil
}

// KeyID returns the active signing key ID.
func (s *Service) KeyID() string { return s.kid }

// Audience returns the registry service/audience string.
func (s *Service) Audience() string { return s.audience }

// Lifetime returns the configured token lifetime.
func (s *Service) Lifetime() time.Duration { return s.lifetime }

// Issue creates a short-lived, scoped registry JWT.
func (s *Service) Issue(subject string, access []ResourceActions) (string, time.Time, error) {
	if subject == "" {
		return "", time.Time{}, fmt.Errorf("registry JWT subject is required")
	}
	if access == nil {
		access = []ResourceActions{}
	}
	if err := validateAccess(access, false); err != nil {
		return "", time.Time{}, err
	}
	now := s.now().UTC().Truncate(time.Second)
	expires := now.Add(s.lifetime)
	tokenIDBytes := make([]byte, 16)
	if _, err := rand.Read(tokenIDBytes); err != nil {
		return "", time.Time{}, fmt.Errorf("generate registry JWT ID: %w", err)
	}
	claims := Claims{
		Claims: jwt.Claims{
			Issuer: s.issuer, Subject: subject, Audience: jwt.Audience{s.audience},
			Expiry: jwt.NewNumericDate(expires), NotBefore: jwt.NewNumericDate(now),
			IssuedAt: jwt.NewNumericDate(now), ID: hex.EncodeToString(tokenIDBytes),
		},
		Access: access,
	}
	raw, err := jwt.Signed(s.signer).Claims(claims).Serialize()
	if err != nil {
		return "", time.Time{}, fmt.Errorf("sign registry JWT: %w", err)
	}
	return raw, expires, nil
}

// Validate verifies signature, identity, time, and access-claim structure.
func (s *Service) Validate(raw string) (*Claims, error) {
	claims, err := s.parseAndVerify(raw)
	if err != nil || !s.hasRequiredClaims(claims) {
		return nil, ErrInvalidToken
	}
	if err := claims.ValidateWithLeeway(jwt.Expected{
		Issuer: s.issuer, AnyAudience: jwt.Audience{s.audience}, Time: s.now().UTC(),
	}, s.leeway); err != nil {
		return nil, ErrInvalidToken
	}
	if !s.hasValidLifetime(claims) {
		return nil, ErrInvalidToken
	}
	if err := validateAccess(claims.Access, true); err != nil {
		return nil, ErrInvalidToken
	}
	return claims, nil
}

func (s *Service) parseAndVerify(raw string) (*Claims, error) {
	token, err := jwt.ParseSigned(raw, []jose.SignatureAlgorithm{jose.RS256})
	if err != nil || len(token.Headers) != 1 {
		return nil, ErrInvalidToken
	}
	header := token.Headers[0]
	if header.Algorithm != string(jose.RS256) || header.KeyID != s.kid {
		return nil, ErrInvalidToken
	}

	var claims Claims
	if err := token.Claims(s.publicKey, &claims); err != nil {
		return nil, ErrInvalidToken
	}
	return &claims, nil
}

func (s *Service) hasRequiredClaims(claims *Claims) bool {
	return claims != nil && claims.Issuer == s.issuer && claims.Subject != "" &&
		len(claims.Audience) == 1 && claims.Audience[0] == s.audience &&
		claims.Expiry != nil && claims.NotBefore != nil && claims.IssuedAt != nil && claims.Access != nil
}

func (s *Service) hasValidLifetime(claims *Claims) bool {
	issuedAt := claims.IssuedAt.Time()
	expires := claims.Expiry.Time()
	notBefore := claims.NotBefore.Time()
	return expires.After(issuedAt) && !notBefore.After(expires) && expires.Sub(issuedAt) <= s.maxAge
}

// Authorize validates raw and requires every requested access item.
func (s *Service) Authorize(raw string, required []ResourceActions) (*Claims, error) {
	claims, err := s.Validate(raw)
	if err != nil {
		return nil, err
	}
	for _, requested := range required {
		for _, action := range requested.Actions {
			if !claims.allow(requested.Type, requested.Name, action) {
				return nil, ErrInsufficientScope
			}
		}
	}
	return claims, nil
}

func (c *Claims) allow(resourceType, name, action string) bool {
	if action == deleteAction {
		action = PushAction
	}
	for _, grant := range c.Access {
		if grant.Type == resourceType && grant.Name == name &&
			(slices.Contains(grant.Actions, action) || slices.Contains(grant.Actions, WildcardAction)) {
			return true
		}
	}
	return false
}

func validateAccess(access []ResourceActions, allowEmptyActions bool) error {
	for _, grant := range access {
		if grant.Type != RepositoryType || !validRepositoryName(grant.Name) || (!allowEmptyActions && len(grant.Actions) == 0) {
			return fmt.Errorf("invalid registry JWT access grant")
		}
		seen := make(map[string]struct{}, len(grant.Actions))
		for _, action := range grant.Actions {
			if action != PullAction && action != PushAction && action != WildcardAction {
				return fmt.Errorf("invalid registry JWT action %q", action)
			}
			if _, ok := seen[action]; ok {
				return fmt.Errorf("duplicate registry JWT action %q", action)
			}
			seen[action] = struct{}{}
		}
	}
	return nil
}

func validRepositoryName(name string) bool {
	if name == "" || strings.HasPrefix(name, "/") || strings.HasSuffix(name, "/") {
		return false
	}
	for _, part := range strings.Split(name, "/") {
		if part == "" || part == "." || part == ".." {
			return false
		}
	}
	return true
}
