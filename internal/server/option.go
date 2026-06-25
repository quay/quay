package server

import (
	"net/http"
)

// Option configures a Server during construction.
type Option func(*options)

type options struct {
	extraRoutes []route
	middleware  func(http.Handler) http.Handler
}

type route struct {
	pattern string
	handler http.Handler
}

// WithRoute adds a route to the server mux before the catch-all distribution handler.
func WithRoute(pattern string, handler http.Handler) Option {
	return func(o *options) {
		o.extraRoutes = append(o.extraRoutes, route{pattern: pattern, handler: handler})
	}
}

// WithMiddleware wraps the top-level handler with middleware.
// Calling this multiple times replaces the previous middleware; compose
// before passing if you need a chain.
func WithMiddleware(mw func(http.Handler) http.Handler) Option {
	return func(o *options) { o.middleware = mw }
}
