package config

// validateRequired checks for fields listed in CONFIG_SCHEMA["required"].
func validateRequired(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	if cfg.SecretKey == "" {
		errs = append(errs, ValidationError{
			Field: "SECRET_KEY", Severity: SeverityError,
			Message: "is required",
		})
	}
	if cfg.DatabaseSecretKey == "" {
		errs = append(errs, ValidationError{
			Field: "DATABASE_SECRET_KEY", Severity: SeverityError,
			Message: "is required",
		})
	}
	if cfg.ServerHostname == "" {
		errs = append(errs, ValidationError{
			Field: "SERVER_HOSTNAME", Severity: SeverityError,
			Message: "is required",
		})
	}
	if cfg.DBURI == "" {
		errs = append(errs, ValidationError{
			Field: "DB_URI", Severity: SeverityError,
			Message: "is required",
		})
	}
	if len(cfg.DistributedStorageConfig) == 0 {
		errs = append(errs, ValidationError{
			Field: "DISTRIBUTED_STORAGE_CONFIG", Severity: SeverityError,
			Message: "is required",
		})
	}
	if cfg.BuildlogsRedis == nil {
		errs = append(errs, ValidationError{
			Field: "BUILDLOGS_REDIS", Severity: SeverityError,
			Message: "is required",
		})
	}
	if cfg.UserEventsRedis == nil {
		errs = append(errs, ValidationError{
			Field: "USER_EVENTS_REDIS", Severity: SeverityError,
			Message: "is required",
		})
	}
	if len(cfg.DistributedStoragePreference) == 0 {
		errs = append(errs, ValidationError{
			Field: "DISTRIBUTED_STORAGE_PREFERENCE", Severity: SeverityError,
			Message: "is required",
		})
	}
	if len(cfg.TagExpirationOptions) == 0 {
		errs = append(errs, ValidationError{
			Field: "TAG_EXPIRATION_OPTIONS", Severity: SeverityError,
			Message: "is required",
		})
	}

	return errs
}
