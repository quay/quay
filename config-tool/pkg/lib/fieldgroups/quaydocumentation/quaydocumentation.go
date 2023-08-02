package quaydocumentation

import (
	"errors"

	"github.com/creasty/defaults"
)

// QuayDocumentationFieldGroup represents the QuayDocumentationFieldGroup config fields
type QuayDocumentationFieldGroup struct {
	DocumentationRoot string `default:"" validate:"" json:"DOCUMENTATION_ROOT,omitempty" yaml:"DOCUMENTATION_ROOT,omitempty"`
}

// NewQuayDocumentationFieldGroup creates a new QuayDocumentationFieldGroup
func NewQuayDocumentationFieldGroup(fullConfig map[string]interface{}) (*QuayDocumentationFieldGroup, error) {
	newQuayDocumentationFieldGroup := &QuayDocumentationFieldGroup{}
	defaults.Set(newQuayDocumentationFieldGroup)

	if value, ok := fullConfig["DOCUMENTATION_ROOT"]; ok {
		newQuayDocumentationFieldGroup.DocumentationRoot, ok = value.(string)
		if !ok {
			return newQuayDocumentationFieldGroup, errors.New("DOCUMENTATION_ROOT must be of type string")
		}
	}

	return newQuayDocumentationFieldGroup, nil
}
