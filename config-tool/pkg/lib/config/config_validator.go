package config

import (
	"github.com/quay/config-tool/pkg/lib/shared"
	log "github.com/sirupsen/logrus"
)

// Validate checks the configuration settings for this field group
func (c Config) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
	configErrors := []shared.ValidationError{}

	// Iterate through field groups and add validator
	for fgName, fg := range c {

		log.Debugf("Validating %s", fgName)

		// Validate specific field group
		fgErrors := fg.Validate(opts)

		// If errors were present, append to config errors
		if len(fgErrors) > 0 {
			configErrors = append(configErrors, fgErrors...)
		}
	}

	// Return errors
	return configErrors
}
