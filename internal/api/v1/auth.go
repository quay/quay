package v1

import (
	"fmt"
	"net/http"
)

// RequireBasic protects a route with HTTP Basic auth.
func (r *Router) RequireBasic(next AuthHandlerFunc) HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request, params Params) {
		result := r.authenticator.Authenticate(req)
		if !result.Authenticated {
			w.Header().Set("WWW-Authenticate", fmt.Sprintf("Basic realm=%q", r.realm))
			if !result.Presented {
				WriteError(w, http.StatusUnauthorized, "authentication required")
				return
			}
			WriteError(w, http.StatusUnauthorized, "authentication failed")
			return
		}

		next(w, req, params, &result.Principal)
	}
}
