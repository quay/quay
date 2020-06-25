package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// DocumentationFieldGroup represents the DocumentationFieldGroup config fields
type DocumentationFieldGroup struct {
	DocumentationRoot string `default:"" validate:""`
}

// NewDocumentationFieldGroup creates a new DocumentationFieldGroup
func NewDocumentationFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newDocumentationFieldGroup := &DocumentationFieldGroup{}
	defaults.Set(newDocumentationFieldGroup)

	if value, ok := fullConfig["DOCUMENTATION_ROOT"]; ok {
		newDocumentationFieldGroup.DocumentationRoot = value.(string)
	}

	return newDocumentationFieldGroup
}

// Validate checks the configuration settings for this field group
func (fg *DocumentationFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()

	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
