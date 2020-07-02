package fieldgroups

import (
	"errors"
	"github.com/creasty/defaults"
)

// DocumentationFieldGroup represents the DocumentationFieldGroup config fields
type DocumentationFieldGroup struct {
	DocumentationRoot string `default:"" validate:""`
}

// NewDocumentationFieldGroup creates a new DocumentationFieldGroup
func NewDocumentationFieldGroup(fullConfig map[string]interface{}) (FieldGroup, error) {
	newDocumentationFieldGroup := &DocumentationFieldGroup{}
	defaults.Set(newDocumentationFieldGroup)

	if value, ok := fullConfig["DOCUMENTATION_ROOT"]; ok {
		newDocumentationFieldGroup.DocumentationRoot, ok = value.(string)
		if !ok {
			return newDocumentationFieldGroup, errors.New("DOCUMENTATION_ROOT must be of type string")
		}
	}

	return newDocumentationFieldGroup, nil
}
