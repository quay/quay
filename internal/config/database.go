package config

import "strings"

// Database holds database connection settings.
type Database struct {
	DBURI            string            `yaml:"DB_URI"`
	DBConnectionArgs *DBConnectionArgs `yaml:"DB_CONNECTION_ARGS"`
}

// DBConnectionArgs contains connection-level database options.
type DBConnectionArgs struct {
	Threadlocals bool       `yaml:"threadlocals"`
	Autorollback bool       `yaml:"autorollback"`
	SSL          *DBSSLArgs `yaml:"ssl"`
}

// DBSSLArgs contains SSL-specific database connection options.
type DBSSLArgs struct {
	CA string `yaml:"ca"`
}

// validateDatabase checks structural validity of database configuration.
// Online connectivity probes are deferred to a future phase.
func validateDatabase(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	if cfg.DBURI != "" {
		validPrefixes := []string{"postgresql://", "sqlite:///"}
		valid := false
		for _, p := range validPrefixes {
			if strings.HasPrefix(cfg.DBURI, p) {
				valid = true
				break
			}
		}
		if !valid {
			errs = append(errs, ValidationError{
				Field: "DB_URI", Severity: SeverityError,
				Message: "must start with postgresql:// or sqlite:///",
			})
		}
	}

	return errs
}
