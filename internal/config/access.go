package config

// AccessLog holds access timestamp tracking settings.
type AccessLog struct {
	LastAccessedUpdateThresholdS int `yaml:"LAST_ACCESSED_UPDATE_THRESHOLD_S"`
}
