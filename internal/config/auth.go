package config

// Auth holds authentication and authorization settings.
type Auth struct {
	AuthenticationType       string   `yaml:"AUTHENTICATION_TYPE"`
	SuperUsers               []string `yaml:"SUPER_USERS"`
	RobotsDisallow           bool     `yaml:"ROBOTS_DISALLOW"`
	RobotsWhitelist          []string `yaml:"ROBOTS_WHITELIST"`
	RegistryJWTAuthMaxFreshS int      `yaml:"REGISTRY_JWT_AUTH_MAX_FRESH_S"`
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
	if cfg.RegistryJWTAuthMaxFreshS < 60 {
		errs = append(errs, ValidationError{
			Field: "REGISTRY_JWT_AUTH_MAX_FRESH_S", Severity: SeverityError,
			Message: "must be at least 60 seconds",
		})
	}

	return errs
}
