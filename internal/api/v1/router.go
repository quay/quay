package v1

import (
	"net/http"
	"sort"
	"strings"

	"github.com/quay/quay/internal/auth"
)

// Params contains path parameters extracted from a route match.
type Params map[string]string

// HandlerFunc handles a matched API request.
type HandlerFunc func(http.ResponseWriter, *http.Request, Params)

// AuthHandlerFunc handles a matched API request after authentication.
type AuthHandlerFunc func(http.ResponseWriter, *http.Request, Params, *auth.Principal)

// Matcher determines whether a route handles a request path.
type Matcher interface {
	Match(path string) (Params, bool)
}

// MatchFunc adapts a function into a Matcher.
type MatchFunc func(path string) (Params, bool)

// Match calls f(path).
func (f MatchFunc) Match(path string) (Params, bool) {
	return f(path)
}

type route struct {
	method  string
	matcher Matcher
	handler HandlerFunc
}

// Router dispatches API v1 routes.
type Router struct {
	authenticator Authenticator
	realm         string
	routes        []route
}

// NewRouter returns an empty API v1 router.
func NewRouter(cfg Config) *Router {
	return &Router{authenticator: cfg.Authenticator, realm: cfg.Realm}
}

// Handle registers a route.
func (r *Router) Handle(method string, matcher Matcher, handler HandlerFunc) {
	r.routes = append(r.routes, route{method: method, matcher: matcher, handler: handler})
}

// ServeHTTP dispatches the request to a registered route.
func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	allowed := make(map[string]bool)
	for _, route := range r.routes {
		params, ok := route.matcher.Match(req.URL.Path)
		if !ok {
			continue
		}
		if route.method != req.Method {
			allowed[route.method] = true
			continue
		}
		route.handler(w, req, params)
		return
	}

	if len(allowed) > 0 {
		w.Header().Set("Allow", strings.Join(sortedMethods(allowed), ", "))
		WriteError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	WriteError(w, http.StatusNotFound, "not found")
}

func sortedMethods(methods map[string]bool) []string {
	result := make([]string, 0, len(methods))
	for method := range methods {
		result = append(result, method)
	}
	sort.Strings(result)
	return result
}
