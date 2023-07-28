package googlelogin

// Fields returns a list of strings representing the fields in this field group
func (fg *GoogleLoginFieldGroup) Fields() []string {
	return []string{"FEATURE_GOOGLE_LOGIN", "GOOGLE_LOGIN_CONFIG"}
}
