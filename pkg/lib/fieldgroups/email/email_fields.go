package email

// Fields returns a list of strings representing the fields in this field group
func (fg *EmailFieldGroup) Fields() []string {
	return []string{"BLACKLISTED_EMAIL_DOMAINS", "FEATURE_BLACKLISTED_EMAILS", "FEATURE_MAILING", "MAIL_DEFAULT_SENDER", "MAIL_PASSWORD", "MAIL_PORT", "MAIL_SERVER", "MAIL_USERNAME", "MAIL_USE_AUTH", "MAIL_USE_TLS"}
}
