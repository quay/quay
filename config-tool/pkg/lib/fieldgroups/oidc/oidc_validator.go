package oidc

import (
	"fmt"
	"strings"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *OIDCFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "OIDC"

	var errors []shared.ValidationError

	// If there are no providers, return no errors
	if len(fg.OIDCProviders) == 0 {
		return errors
	}

	// Loop through providers
	for _, provider := range fg.OIDCProviders {

		schemaErrors := 0
		// Check required fields are present
		if ok, err := shared.ValidateRequiredString(provider.OIDCServer, fmt.Sprintf("%s_LOGIN_CONFIG.OIDC_SERVER", strings.ToUpper(provider._Prefix)), fgName); !ok {
			errors = append(errors, err)
			schemaErrors++
		}
		if ok, err := shared.ValidateRequiredString(provider.ClientID, fmt.Sprintf("%s_LOGIN_CONFIG.CLIENT_ID", strings.ToUpper(provider._Prefix)), fgName); !ok {
			errors = append(errors, err)
			schemaErrors++

		}
		if ok, err := shared.ValidateRequiredString(provider.ClientSecret, fmt.Sprintf("%s_LOGIN_CONFIG.CLIENT_SECRET", strings.ToUpper(provider._Prefix)), fgName); !ok {
			errors = append(errors, err)
			schemaErrors++

		}
		if ok, err := shared.ValidateRequiredString(provider.ServiceName, fmt.Sprintf("%s_LOGIN_CONFIG.SERVICE_NAME", strings.ToUpper(provider._Prefix)), fgName); !ok {
			errors = append(errors, err)
			schemaErrors++
		}

		if schemaErrors > 0 {
			continue
		}

		if ok, err := shared.ValidateOIDCServer(opts, provider.OIDCServer, provider.ClientID, provider.ClientSecret, provider.ServiceName, provider.LoginScopes, fgName); !ok {
			errors = append(errors, err)
		}

	}

	return errors

}
