package jwtauth

import (
	"errors"
	"fmt"
	"strings"
)

// ChallengeValue builds a Docker Registry Bearer challenge value.
func ChallengeValue(realm, service string, access []ResourceActions, authErr error) string {
	value := fmt.Sprintf("Bearer realm=%q,service=%q", realm, service)
	if scope := ScopeParam(access); scope != "" {
		value += fmt.Sprintf(",scope=%q", scope)
	}
	switch {
	case errors.Is(authErr, ErrInvalidToken):
		value += `,error="invalid_token"`
	case errors.Is(authErr, ErrInsufficientScope):
		value += `,error="insufficient_scope"`
	}
	return value
}

// ScopeParam returns the space-separated Docker scope representation.
func ScopeParam(access []ResourceActions) string {
	scopes := make([]string, 0, len(access))
	for _, grant := range access {
		if grant.Type == "" || grant.Name == "" || len(grant.Actions) == 0 {
			continue
		}
		scopes = append(scopes, fmt.Sprintf("%s:%s:%s", grant.Type, grant.Name, strings.Join(grant.Actions, ",")))
	}
	return strings.Join(scopes, " ")
}
