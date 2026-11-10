package config

// Auth holds authentication and authorization settings.
type Auth struct {
	AuthenticationType  string   `yaml:"AUTHENTICATION_TYPE"`
	SuperUsers          []string `yaml:"SUPER_USERS"`
	RobotsDisallow      bool     `yaml:"ROBOTS_DISALLOW"`
	RobotsWhitelist     []string `yaml:"ROBOTS_WHITELIST"`
	CreatePrivateOnPush bool     `yaml:"CREATE_PRIVATE_REPO_ON_PUSH"`
	// PasswordAuthCacheTTLS is how many seconds a successful password
	// verification is remembered so repeat logins with the same credentials
	// skip the bcrypt comparison. 0 disables the cache.
	PasswordAuthCacheTTLS int `yaml:"PASSWORD_AUTH_CACHE_TTL_S"`
}

// validateAuth checks authentication enum values.
func validateAuth(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	if cfg.PasswordAuthCacheTTLS < 0 {
		errs = append(errs, ValidationError{
			Field: "PASSWORD_AUTH_CACHE_TTL_S", Severity: SeverityError,
			Message: "must be 0 (disabled) or a positive number of seconds",
		})
	}

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
