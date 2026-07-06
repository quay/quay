// Package v1 implements composable Go-backed Quay API v1 surfaces.
package v1

import (
	"fmt"
	"net/http"

	"github.com/quay/quay/internal/auth"
)

// Module registers a selectable API surface.
type Module interface {
	Register(*Router)
}

// Config holds dependencies shared by API v1 modules.
type Config struct {
	Authenticator Authenticator
	Realm         string
}

// Authenticator validates requests for protected API routes.
type Authenticator interface {
	Authenticate(*http.Request) auth.Result
}

// New returns an API v1 HTTP handler with the supplied modules registered.
func New(cfg Config, modules ...Module) (http.Handler, error) {
	if cfg.Authenticator == nil {
		return nil, fmt.Errorf("nil authenticator")
	}
	if cfg.Realm == "" {
		cfg.Realm = "Quay API"
	}

	router := NewRouter(cfg)
	for _, module := range modules {
		if module == nil {
			continue
		}
		module.Register(router)
	}
	return router, nil
}
