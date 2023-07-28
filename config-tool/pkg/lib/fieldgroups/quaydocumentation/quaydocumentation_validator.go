package quaydocumentation

import (
	"net/url"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *QuayDocumentationFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "QuayDocumentation"

	// Make empty errors
	errors := []shared.ValidationError{}

	// If not provided, skip
	if fg.DocumentationRoot == "" {
		return errors
	}

	// Make sure documentation root is valid url
	if _, err := url.ParseRequestURI(fg.DocumentationRoot); err != nil {
		newError := shared.ValidationError{
			Tags:       []string{"DOCUMENTATION_ROOT"},
			FieldGroup: fgName,
			Message:    "Documentation root must be a valid url.",
		}
		errors = append(errors, newError)
	}

	return errors

}
