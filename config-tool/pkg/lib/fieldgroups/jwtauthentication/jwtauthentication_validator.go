package jwtauthentication

import (
	"strings"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *JWTAuthenticationFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "JWTAuthentication"

	var errors []shared.ValidationError

	// If auth type is not JWT, return
	if fg.AuthenticationType != "JWT" {
		return errors
	}

	// Check for verify endpoint
	if fg.JwtVerifyEndpoint == "" {
		newError := shared.ValidationError{
			Tags:       []string{"JWT_VERIFY_ENDPOINT"},
			FieldGroup: fgName,
			Message:    "JWT_VERIFY_ENDPOINT is required",
		}
		errors = append(errors, newError)
	}
	// Check verify endpoint has right form endpoint
	if !strings.HasPrefix(fg.JwtVerifyEndpoint, "http://") && !strings.HasPrefix(fg.JwtVerifyEndpoint, "https://") {
		newError := shared.ValidationError{
			Tags:       []string{"JWT_VERIFY_ENDPOINT"},
			FieldGroup: fgName,
			Message:    "JWT_VERIFY_ENDPOINT must be a url",
		}
		errors = append(errors, newError)
	}

	// If get user endpoint, make sure it is right form
	if fg.JwtGetuserEndpoint != "" {
		if !strings.HasPrefix(fg.JwtGetuserEndpoint, "http://") && !strings.HasPrefix(fg.JwtGetuserEndpoint, "https://") {
			newError := shared.ValidationError{
				Tags:       []string{"JWT_GETUSER_ENDPOINT"},
				FieldGroup: fgName,
				Message:    "JWT_GETUSER_ENDPOINT must be a url",
			}
			errors = append(errors, newError)
		}
	}

	// If get user endpoint, make sure it is right form
	if fg.JwtQueryEndpoint != "" {
		if !strings.HasPrefix(fg.JwtQueryEndpoint, "http://") && !strings.HasPrefix(fg.JwtQueryEndpoint, "https://") {
			newError := shared.ValidationError{
				Tags:       []string{"JWT_QUERY_ENDPOINT"},
				FieldGroup: fgName,
				Message:    "JWT_QUERY_ENDPOINT must be a url",
			}
			errors = append(errors, newError)
		}
	}

	// Check for config
	if fg.JwtAuthIssuer == "" {
		newError := shared.ValidationError{
			Tags:       []string{"JWT_AUTH_ISSUER"},
			FieldGroup: fgName,
			Message:    "JWT_AUTH_ISSUER is required for JWT",
		}
		errors = append(errors, newError)
	}

	return errors

}
