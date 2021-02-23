package ldap

import (
	"fmt"
	"math"
	"net/url"
	"strings"

	"github.com/go-ldap/ldap/v3"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *LDAPFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "LDAP"

	// Make empty errors
	errors := []shared.ValidationError{}

	// Check authentication type
	if fg.AuthenticationType != "LDAP" {
		return errors
	}

	// check that admin dn is present
	if ok, err := shared.ValidateRequiredString(fg.LdapAdminDn, "LDAP_ADMIN_DN", fgName); !ok {
		errors = append(errors, err)
	}

	// check that admin pass is present
	if ok, err := shared.ValidateRequiredString(fg.LdapAdminPasswd, "LDAP_ADMIN_PASSWD", fgName); !ok {
		errors = append(errors, err)
	}

	// Parse url
	uri, err := url.Parse(fg.LdapUri)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"LDAP"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	if ok, err := shared.ValidateIsOneOfString(uri.Scheme, []string{"ldap", "ldaps"}, "LDAP_URI", fgName); !ok {
		errors = append(errors, err)
		return errors
	}

	// Get tls config
	tlsConfig, err := shared.GetTlsConfig(opts)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"LDAP"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	// Check for LDAP ca cert and add if present
	if crt, ok := opts.Certificates["ldap.crt"]; ok {
		certAdded := tlsConfig.RootCAs.AppendCertsFromPEM(crt)
		if !certAdded {
			newError := shared.ValidationError{
				Tags:       []string{"LDAP"},
				FieldGroup: fgName,
				Message:    "Could not successfully load ldap.crt",
			}
			errors = append(errors, newError)
			return errors
		}
	}

	// Dial ldap server
	l, err := ldap.DialURL(fg.LdapUri, ldap.DialWithTLSConfig(tlsConfig))
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"LDAP_URI"},
			FieldGroup: fgName,
			Message:    "Could not connect to " + fg.LdapUri + ". Error: " + err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	// Authenticate
	err = l.Bind(fg.LdapAdminDn, fg.LdapAdminPasswd)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"LDAP_URI"},
			FieldGroup: fgName,
			Message:    "Could not authenticate LDAP server. Error: " + err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	userFilter := fmt.Sprintf("(&(%s=*)%s)", fg.LdapUidAttr, fg.LdapUserFilter)
	request := &ldap.SearchRequest{
		BaseDN: strings.Join(shared.InterfaceArrayToStringArray(fg.LdapBaseDn), ","),
		Scope:  ldap.ScopeWholeSubtree,
		Filter: userFilter,
		Attributes: []string{
			fg.LdapEmailAttr, fg.LdapUidAttr,
		},
		SizeLimit: math.MaxInt32,
	}

	result, err := l.SearchWithPaging(request, math.MaxInt32)
	if err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"LDAP_URI"},
			FieldGroup: fgName,
			Message:    "Could not query LDAP server. Error: " + err.Error(),
		}
		errors = append(errors, newError)
		return errors
	}

	if len(result.Entries) < 1 {
		newError := shared.ValidationError{
			Tags:       []string{"LDAP_URI"},
			FieldGroup: fgName,
			Message:    "Could not find any users matching filter in LDAP server",
		}
		errors = append(errors, newError)
		return errors
	}

	return errors
}
