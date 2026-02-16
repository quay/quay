package config

// Auth holds authentication and authorization settings.
type Auth struct {
	AuthenticationType string   `yaml:"AUTHENTICATION_TYPE"`
	SuperUsers         []string `yaml:"SUPER_USERS"`
}

// validateAuth checks authentication enum values.
func validateAuth(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	switch cfg.AuthenticationType {
	case "Database", "LDAP", "JWT", "Keystone", "OIDC", "AppToken":
		// valid
	default:
		errs = append(errs, ValidationError{
			Field: "AUTHENTICATION_TYPE", Severity: SeverityError,
			Message: `must be one of: "Database", "LDAP", "JWT", "Keystone", "OIDC", "AppToken"`,
		})
	}

	return errs
}
