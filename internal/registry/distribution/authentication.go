package distribution

import (
	"context"
	"database/sql"
	"fmt"
	"net/http"
	"net/url"
	"time"

	quayauth "github.com/quay/quay/internal/auth"
	registryauth "github.com/quay/quay/internal/registry/auth"
)

const (
	registryTokenLifetime  = 5 * time.Minute
	registryTokenClockSkew = 5 * time.Second
)

// AuthenticationConfig configures registry token issuance and authorization.
type AuthenticationConfig struct {
	Scheme               string
	Service              string
	LibraryNamespace     string
	AnonymousAccess      bool
	MaxTokenFreshness    time.Duration
	SuperUsers           []string
	SuperUsersFullAccess bool
}

// Authentication holds the shared registry access controller and token endpoint.
type Authentication struct {
	Controller   *registryauth.Controller
	TokenHandler http.Handler
}

// NewAuthentication constructs the complete registry bearer-token flow.
func NewAuthentication(db *sql.DB, credentialVerifier quayauth.Verifier, cfg *AuthenticationConfig) (*Authentication, error) {
	if cfg == nil {
		return nil, fmt.Errorf("nil authentication config")
	}
	if credentialVerifier == nil {
		return nil, fmt.Errorf("nil credential verifier")
	}

	grantResolver, err := NewGrantResolver(db, GrantResolverConfig{
		LibraryNamespace: cfg.LibraryNamespace, SuperUsers: cfg.SuperUsers,
		SuperUsersFullAccess: cfg.SuperUsersFullAccess,
	})
	if err != nil {
		return nil, fmt.Errorf("create registry grant resolver: %w", err)
	}

	signer, verifier, err := registryauth.NewES256Pair(registryauth.ES256Config{
		Issuer: registryauth.Issuer, Audience: cfg.Service,
		MaxFresh: cfg.MaxTokenFreshness, ClockSkew: registryTokenClockSkew,
	})
	if err != nil {
		return nil, fmt.Errorf("create registry token keys: %w", err)
	}
	realm := (&url.URL{Scheme: cfg.Scheme, Host: cfg.Service, Path: "/v2/auth"}).String()
	controller, err := registryauth.NewController(registryauth.ControllerConfig{
		Realm: realm, Service: cfg.Service, LibraryNamespace: cfg.LibraryNamespace, Verifier: verifier,
	})
	if err != nil {
		return nil, fmt.Errorf("create registry access controller: %w", err)
	}

	tokenLifetime := min(registryTokenLifetime, cfg.MaxTokenFreshness)
	tokenHandler, err := registryauth.NewHandler(&registryauth.HandlerConfig{
		Service: cfg.Service, LibraryNamespace: cfg.LibraryNamespace,
		AnonymousAccess: cfg.AnonymousAccess, Lifetime: tokenLifetime, Signer: signer,
		Authenticate: func(ctx context.Context, username, secret string) (registryauth.Identity, bool) {
			result := credentialVerifier.Verify(ctx, quayauth.Credentials{Username: username, Secret: secret})
			if !result.Authenticated {
				return registryauth.Identity{}, false
			}
			principal := result.Principal
			return registryauth.Identity{Subject: principal.Username, Principal: &principal}, true
		},
		ResolveGrants: grantResolver.Resolve,
	})
	if err != nil {
		return nil, fmt.Errorf("create registry token handler: %w", err)
	}

	return &Authentication{Controller: controller, TokenHandler: tokenHandler}, nil
}
