package lib

// BlacklistEmailFieldGroup is a FieldGroup representing the Blackmail Email settings
type BlacklistEmailFieldGroup struct {

	// If set to true, no new User accounts may be created if their email domain is blacklisted.
	FeatureBlacklistedEmails bool `yaml:"FEATURE_BLACKLISTED_EMAILS,omitempty"`

	// The array of email-address domains that is used if FEATURE_BLACKLISTED_EMAILS is set to true.
	BlacklistedEmailDomains []string `yaml:"BLACKLISTED_EMAIL_DOMAINS,omitempty"`
}

// Validate assures that the field group contains valid settings
func (fg *BlacklistEmailFieldGroup) Validate() (bool, error) {
	return true, nil
}
