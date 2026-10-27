package config

import "fmt"

// Server holds hosting and presentation settings.
type Server struct {
	ServerHostname         string   `yaml:"SERVER_HOSTNAME"`
	PreferredURLScheme     string   `yaml:"PREFERRED_URL_SCHEME"`
	ExternalTLSTermination *bool    `yaml:"EXTERNAL_TLS_TERMINATION"`
	SSLProtocols           []string `yaml:"SSL_PROTOCOLS"`
	RegistryTitle          string   `yaml:"REGISTRY_TITLE"`
	RegistryTitleShort     string   `yaml:"REGISTRY_TITLE_SHORT"`
	RegistryState          string   `yaml:"REGISTRY_STATE"`
	LibraryNamespace       string   `yaml:"LIBRARY_NAMESPACE"`
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

	errs = append(errs, validateSSLProtocols(cfg.SSLProtocols)...)

	return errs
}

var validSSLProtocols = map[string]bool{
	"TLSv1.2": true,
	"TLSv1.3": true,
}

func validateSSLProtocols(protocols []string) []ValidationError {
	var errs []ValidationError
	for _, p := range protocols {
		if !validSSLProtocols[p] {
			errs = append(errs, ValidationError{
				Field: "SSL_PROTOCOLS", Severity: SeverityError,
				Message: fmt.Sprintf("unsupported protocol %q; valid values are TLSv1.2, TLSv1.3", p),
			})
		}
	}
	return errs
}
