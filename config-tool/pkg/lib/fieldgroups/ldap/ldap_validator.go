package ldap

import (
	"net/url"

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

	if ok, err := shared.ValidateLDAPServer(opts, fg.LdapUri, fg.LdapAdminDn, fg.LdapAdminPasswd, fg.LdapUidAttr, fg.LdapEmailAttr, fg.LdapUserFilter, fg.LdapBaseDn, fgName); !ok {
		errors = append(errors, err)
		return errors
	}

	return errors
}
