package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// TagExpirationFieldGroup represents the TagExpirationFieldGroup config fields
type TagExpirationFieldGroup struct {
	FeatureChangeTagExpiration bool          `default:"false" validate:""`
	DefaultTagExpiration       string        `default:"2w" validate:"required"`
	TagExpirationOptions       []interface{} `default:"[\"0s\", \"1d\", \"1w\", \"2w\", \"4w\"]" validate:"required"`
}

// NewTagExpirationFieldGroup creates a new TagExpirationFieldGroup
func NewTagExpirationFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newTagExpirationFieldGroup := &TagExpirationFieldGroup{}
	defaults.Set(newTagExpirationFieldGroup)

	if value, ok := fullConfig["FEATURE_CHANGE_TAG_EXPIRATION"]; ok {
		newTagExpirationFieldGroup.FeatureChangeTagExpiration = value.(bool)
	}
	if value, ok := fullConfig["DEFAULT_TAG_EXPIRATION"]; ok {
		newTagExpirationFieldGroup.DefaultTagExpiration = value.(string)
	}
	if value, ok := fullConfig["TAG_EXPIRATION_OPTIONS"]; ok {
		newTagExpirationFieldGroup.TagExpirationOptions = value.([]interface{})
	}

	return newTagExpirationFieldGroup
}

// Validate checks the configuration settings for this field group
func (fg *TagExpirationFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()
	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
