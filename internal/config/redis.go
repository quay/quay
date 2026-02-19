package config

// Redis holds Redis connection configuration for each Quay subsystem.
type Redis struct {
	BuildlogsRedis   *RedisConnection `yaml:"BUILDLOGS_REDIS"`
	UserEventsRedis  *RedisConnection `yaml:"USER_EVENTS_REDIS"`
	PullMetricsRedis *RedisConnection `yaml:"PULL_METRICS_REDIS"`
}

// RedisConnection describes a single Redis endpoint.
type RedisConnection struct {
	Host     string `yaml:"host"`
	Port     int    `yaml:"port"`
	Password string `yaml:"password"` //nolint:gosec // G117: Password is a legitimate config field
	DB       int    `yaml:"db"`
	SSL      bool   `yaml:"ssl"`
}

// validateRedis checks that Redis blocks have required fields when present.
func validateRedis(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	if cfg.BuildlogsRedis != nil && cfg.BuildlogsRedis.Host == "" {
		errs = append(errs, ValidationError{
			Field: "BUILDLOGS_REDIS", Severity: SeverityError,
			Message: "host is required when BUILDLOGS_REDIS is specified",
		})
	}

	if cfg.UserEventsRedis != nil && cfg.UserEventsRedis.Host == "" {
		errs = append(errs, ValidationError{
			Field: "USER_EVENTS_REDIS", Severity: SeverityError,
			Message: "host is required when USER_EVENTS_REDIS is specified",
		})
	}

	if cfg.PullMetricsRedis != nil && cfg.PullMetricsRedis.Host == "" {
		errs = append(errs, ValidationError{
			Field: "PULL_METRICS_REDIS", Severity: SeverityError,
			Message: "host is required when PULL_METRICS_REDIS is specified",
		})
	}

	return errs
}
