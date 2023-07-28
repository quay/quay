package buildmanager

import (

	//mysql driver
	_ "github.com/lib/pq" // postgres driver
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *BuildManagerFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// Return errors
	return errors

}
