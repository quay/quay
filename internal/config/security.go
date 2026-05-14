package config

import "strings"

// Security holds security scanner settings.
type Security struct {
	SecurityScannerV4Endpoint string `yaml:"SECURITY_SCANNER_V4_ENDPOINT"`
}

// validateSecurity checks security scanner settings.
func validateSecurity(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	if cfg.SecurityScannerV4Endpoint != "" {
		if !strings.HasPrefix(cfg.SecurityScannerV4Endpoint, "http://") &&
			!strings.HasPrefix(cfg.SecurityScannerV4Endpoint, "https://") {
			errs = append(errs, ValidationError{
				Field: "SECURITY_SCANNER_V4_ENDPOINT", Severity: SeverityError,
				Message: "must start with http:// or https://",
			})
		}
	}

	return errs
}
