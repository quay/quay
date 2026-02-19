package config

// Server holds hosting and presentation settings.
type Server struct {
	ServerHostname         string `yaml:"SERVER_HOSTNAME"`
	PreferredURLScheme     string `yaml:"PREFERRED_URL_SCHEME"`
	ExternalTLSTermination *bool  `yaml:"EXTERNAL_TLS_TERMINATION"`
	RegistryTitle          string `yaml:"REGISTRY_TITLE"`
	RegistryTitleShort     string `yaml:"REGISTRY_TITLE_SHORT"`
	RegistryState          string `yaml:"REGISTRY_STATE"`
}

// validateServer checks server-related enum values and TLS consistency.
func validateServer(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	switch cfg.PreferredURLScheme {
	case DefaultPreferredURLScheme, "https":
		// valid
	default:
		errs = append(errs, ValidationError{
			Field: "PREFERRED_URL_SCHEME", Severity: SeverityError,
			Message: "must be \"http\" or \"https\"",
		})
	}

	if cfg.RegistryState != "" {
		switch cfg.RegistryState {
		case "normal", "readonly":
			// valid
		default:
			errs = append(errs, ValidationError{
				Field: "REGISTRY_STATE", Severity: SeverityError,
				Message: "must be \"normal\" or \"readonly\"",
			})
		}
	}

	// Warn if using HTTP without TLS termination.
	if cfg.PreferredURLScheme == DefaultPreferredURLScheme && (cfg.ExternalTLSTermination == nil || !*cfg.ExternalTLSTermination) {
		errs = append(errs, ValidationError{
			Field: "PREFERRED_URL_SCHEME", Severity: SeverityWarning,
			Message: "using HTTP without TLS; consider HTTPS or setting EXTERNAL_TLS_TERMINATION",
		})
	}

	return errs
}
