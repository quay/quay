package apptokenauthentication

// Fields returns a list of strings representing the fields in this field group
func (fg *AppTokenAuthenticationFieldGroup) Fields() []string {
	return []string{"AUTHENTICATION_TYPE", "FEATURE_APP_SPECIFIC_TOKENS", "FEATURE_DIRECT_LOGIN"}
}
