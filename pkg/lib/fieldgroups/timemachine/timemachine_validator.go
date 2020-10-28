package timemachine

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *TimeMachineFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "TimeMachine"

	// Make empty errors
	errors := []shared.ValidationError{}

	if ok, err := shared.ValidateIsOneOfString(fg.DefaultTagExpiration, shared.InterfaceArrayToStringArray(fg.TagExpirationOptions), "DEFAULT_TAG_EXPIRATION", fgName); !ok {
		errors = append(errors, err)
		return errors
	}

	return errors
}
