package ldap

import (
	"errors"

	"github.com/creasty/defaults"
)

// LDAPFieldGroup represents the LDAPFieldGroup config fields
type LDAPFieldGroup struct {
	AuthenticationType        string        `default:"Database" validate:"" json:"AUTHENTICATION_TYPE,omitempty" yaml:"AUTHENTICATION_TYPE,omitempty"`
	LdapAdminDn               string        `default:"" validate:"" json:"LDAP_ADMIN_DN,omitempty" yaml:"LDAP_ADMIN_DN,omitempty"`
	LdapAdminPasswd           string        `default:"" validate:"" json:"LDAP_ADMIN_PASSWD,omitempty" yaml:"LDAP_ADMIN_PASSWD,omitempty"`
	LdapAllowInsecureFallback bool          `default:"false" validate:"" json:"LDAP_ALLOW_INSECURE_FALLBACK,omitempty" yaml:"LDAP_ALLOW_INSECURE_FALLBACK,omitempty"`
	LdapBaseDn                []interface{} `default:"" validate:"" json:"LDAP_BASE_DN,omitempty" yaml:"LDAP_BASE_DN,omitempty"`
	LdapEmailAttr             string        `default:"mail" validate:"" json:"LDAP_EMAIL_ATTR,omitempty" yaml:"LDAP_EMAIL_ATTR,omitempty"`
	LdapUidAttr               string        `default:"uid" validate:"" json:"LDAP_UID_ATTR,omitempty" yaml:"LDAP_UID_ATTR,omitempty"`
	LdapUri                   string        `default:"ldap://localhost" validate:"" json:"LDAP_URI,omitempty" yaml:"LDAP_URI,omitempty"`
	LdapUserFilter            string        `default:"" validate:"" json:"LDAP_USER_FILTER,omitempty" yaml:"LDAP_USER_FILTER,omitempty"`
	LdapUserRdn               []interface{} `default:"[]" validate:"" json:"LDAP_USER_RDN,omitempty" yaml:"LDAP_USER_RDN,omitempty"`
}

// NewLDAPFieldGroup creates a new LDAPFieldGroup
func NewLDAPFieldGroup(fullConfig map[string]interface{}) (*LDAPFieldGroup, error) {
	newLDAPFieldGroup := &LDAPFieldGroup{}
	defaults.Set(newLDAPFieldGroup)

	if value, ok := fullConfig["AUTHENTICATION_TYPE"]; ok {
		newLDAPFieldGroup.AuthenticationType, ok = value.(string)
		if !ok {
			return newLDAPFieldGroup, errors.New("AUTHENTICATION_TYPE must be of type string")
		}
	}

	if value, ok := fullConfig["LDAP_ADMIN_DN"]; ok {
		newLDAPFieldGroup.LdapAdminDn, ok = value.(string)
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_ADMIN_DN must be of type string")
		}
	}
	if value, ok := fullConfig["LDAP_ADMIN_PASSWD"]; ok {
		newLDAPFieldGroup.LdapAdminPasswd, ok = value.(string)
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_ADMIN_PASSWD must be of type string")
		}
	}
	if value, ok := fullConfig["LDAP_ALLOW_INSECURE_FALLBACK"]; ok {
		newLDAPFieldGroup.LdapAllowInsecureFallback, ok = value.(bool)
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_ALLOW_INSECURE_FALLBACK must be of type bool")
		}
	}
	if value, ok := fullConfig["LDAP_BASE_DN"]; ok {
		newLDAPFieldGroup.LdapBaseDn, ok = value.([]interface{})
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_BASE_DN must be of type array")
		}
	}
	if value, ok := fullConfig["LDAP_EMAIL_ATTR"]; ok {
		newLDAPFieldGroup.LdapEmailAttr, ok = value.(string)
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_EMAIL_ATTR must be of type string")
		}
	}
	if value, ok := fullConfig["LDAP_UID_ATTR"]; ok {
		newLDAPFieldGroup.LdapUidAttr, ok = value.(string)
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_UID_ATTR must be of type string")
		}
	}
	if value, ok := fullConfig["LDAP_URI"]; ok {
		newLDAPFieldGroup.LdapUri, ok = value.(string)
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_URI must be of type string")
		}
	}
	if value, ok := fullConfig["LDAP_USER_FILTER"]; ok {
		newLDAPFieldGroup.LdapUserFilter, ok = value.(string)
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_USER_FILTER must be of type string")
		}
	}
	if value, ok := fullConfig["LDAP_USER_RDN"]; ok {
		newLDAPFieldGroup.LdapUserRdn, ok = value.([]interface{})
		if !ok {
			return newLDAPFieldGroup, errors.New("LDAP_USER_RDN must be of type []interface{}")
		}
	}

	return newLDAPFieldGroup, nil
}
