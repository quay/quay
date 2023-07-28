package ldap

// Fields returns a list of strings representing the fields in this field group
func (fg *LDAPFieldGroup) Fields() []string {
	return []string{"LDAP_ADMIN_DN", "LDAP_ADMIN_PASSWD", "LDAP_ALLOW_INSECURE_FALLBACK", "LDAP_BASE_DN", "LDAP_EMAIL_ATTR", "LDAP_UID_ATTR", "LDAP_URI", "LDAP_USER_FILTER", "LDAP_USER_RDN"}
}
