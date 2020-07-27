package hostsettings

// Fields returns a list of strings representing the fields in this field group
func (fg *HostSettingsFieldGroup) Fields() []string {
	return []string{"EXTERNAL_TLS_TERMINATION", "PREFERRED_URL_SCHEME", "SERVER_HOSTNAME"}
}
