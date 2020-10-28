package timemachine

import (
	"errors"

	"github.com/creasty/defaults"
)

// TimeMachineFieldGroup represents the TimeMachineFieldGroup config fields
type TimeMachineFieldGroup struct {
	DefaultTagExpiration       string        `default:"2w" validate:"" json:"DEFAULT_TAG_EXPIRATION,omitempty" yaml:"DEFAULT_TAG_EXPIRATION,omitempty"`
	FeatureChangeTagExpiration bool          `default:"true" validate:"" json:"FEATURE_CHANGE_TAG_EXPIRATION,omitempty" yaml:"FEATURE_CHANGE_TAG_EXPIRATION,omitempty"`
	TagExpirationOptions       []interface{} `default:"" validate:"" json:"TAG_EXPIRATION_OPTIONS,omitempty" yaml:"TAG_EXPIRATION_OPTIONS,omitempty"`
}

// NewTimeMachineFieldGroup creates a new TimeMachineFieldGroup
func NewTimeMachineFieldGroup(fullConfig map[string]interface{}) (*TimeMachineFieldGroup, error) {
	newTimeMachineFieldGroup := &TimeMachineFieldGroup{}
	defaults.Set(newTimeMachineFieldGroup)

	if value, ok := fullConfig["DEFAULT_TAG_EXPIRATION"]; ok {
		newTimeMachineFieldGroup.DefaultTagExpiration, ok = value.(string)
		if !ok {
			return newTimeMachineFieldGroup, errors.New("DEFAULT_TAG_EXPIRATION must be of type string")
		}
	}
	if value, ok := fullConfig["FEATURE_CHANGE_TAG_EXPIRATION"]; ok {
		newTimeMachineFieldGroup.FeatureChangeTagExpiration, ok = value.(bool)
		if !ok {
			return newTimeMachineFieldGroup, errors.New("FEATURE_CHANGE_TAG_EXPIRATION must be of type bool")
		}
	}
	if value, ok := fullConfig["TAG_EXPIRATION_OPTIONS"]; ok {
		newTimeMachineFieldGroup.TagExpirationOptions, ok = value.([]interface{})
		if !ok {
			return newTimeMachineFieldGroup, errors.New("TAG_EXPIRATION_OPTIONS must be of type []interface{}")
		}
	} else {
		newTimeMachineFieldGroup.TagExpirationOptions = []interface{}{"0s", "1d", "1w", "2w", "4w"}
	}

	return newTimeMachineFieldGroup, nil
}
