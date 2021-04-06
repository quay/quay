package oidc

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	goOIDC "github.com/coreos/go-oidc"
	"github.com/quay/config-tool/pkg/lib/shared"
	"golang.org/x/oauth2"
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

		// Create http client
		config, err := shared.GetTlsConfig(opts)
		if err != nil {
			newError := shared.ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    err.Error(),
			}
			errors = append(errors, newError)
		}
		tr := &http.Transport{TLSClientConfig: config}
		client := &http.Client{Transport: tr, Timeout: 5 * time.Second}

		ctx := goOIDC.ClientContext(context.Background(), client)

		if !strings.HasSuffix(provider.OIDCServer, "/") {
			newError := shared.ValidationError{
				Tags:       []string{"OIDC_SERVER"},
				FieldGroup: fgName,
				Message:    "OIDC_SERVER must end with a trailing /",
			}
			errors = append(errors, newError)
			continue
		}

		// Create provider
		p, err := goOIDC.NewProvider(ctx, provider.OIDCServer)
		if err != nil {
			p, err = goOIDC.NewProvider(ctx, strings.TrimSuffix(provider.OIDCServer, "/"))
			if err != nil {
				newError := shared.ValidationError{
					Tags:       []string{"OIDC_SERVER"},
					FieldGroup: fgName,
					Message:    "Could not create provider for " + provider.ServiceName + ". Error: " + err.Error(),
				}
				errors = append(errors, newError)
				continue
			}
		}

		oauth2Config := oauth2.Config{
			ClientID:     provider.ClientID,
			ClientSecret: provider.ClientSecret,
			Endpoint:     p.Endpoint(),
			RedirectURL:  "http://quay/oauth2/auth0/callback",
			Scopes:       shared.InterfaceArrayToStringArray(provider.LoginScopes),
		}

		_, err = oauth2Config.Exchange(ctx, "badcode")
		if err != nil {
			if strings.Contains(err.Error(), "access_denied") {
				newError := shared.ValidationError{
					Tags:       []string{"OIDC_SERVER"},
					FieldGroup: fgName,
					Message:    fmt.Sprintf("Incorrect credentials for OIDC %s", provider.ServiceName),
				}
				errors = append(errors, newError)
			} else if strings.Contains(err.Error(), "invalid_grant") {
				continue // this means we connected to the server correctly
			} else {
				newError := shared.ValidationError{
					Tags:       []string{"OIDC_SERVER"},
					FieldGroup: fgName,
					Message:    "Could not reach OIDC server " + provider.ServiceName + ". Error: " + err.Error(),
				}
				errors = append(errors, newError)
			}
		}
	}

	return errors

}
