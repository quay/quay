package config

// validateRequired checks for fields listed in CONFIG_SCHEMA["required"].
func validateRequired(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	if cfg.SecretKey == "" {
		errs = append(errs, ValidationError{
			Field: fieldSecretKey, Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if cfg.DatabaseSecretKey == "" {
		errs = append(errs, ValidationError{
			Field: fieldDatabaseSecretKey, Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if cfg.ServerHostname == "" {
		errs = append(errs, ValidationError{
			Field: "SERVER_HOSTNAME", Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if cfg.DBURI == "" {
		errs = append(errs, ValidationError{
			Field: fieldDBURI, Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if len(cfg.DistributedStorageConfig) == 0 {
		errs = append(errs, ValidationError{
			Field: "DISTRIBUTED_STORAGE_CONFIG", Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if cfg.BuildlogsRedis == nil {
		errs = append(errs, ValidationError{
			Field: fieldBuildlogsRedis, Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if cfg.UserEventsRedis == nil {
		errs = append(errs, ValidationError{
			Field: fieldUserEventsRedis, Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if len(cfg.DistributedStoragePreference) == 0 {
		errs = append(errs, ValidationError{
			Field: fieldDistributedStoragePreference, Severity: SeverityError,
			Message: msgRequired,
		})
	}
	if len(cfg.TagExpirationOptions) == 0 {
		errs = append(errs, ValidationError{
			Field: fieldTagExpirationOptions, Severity: SeverityError,
			Message: msgRequired,
		})
	}

	return errs
}
