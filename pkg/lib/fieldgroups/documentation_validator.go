package fieldgroups

import "net/url"

// Validate checks the configuration settings for this field group
func (fg *DocumentationFieldGroup) Validate() []ValidationError {

	// Make empty errors
	errors := []ValidationError{}

	// If not provided, skip
	if fg.DocumentationRoot == "" {
		return errors
	}

	// Make sure documentation root is valid url
	if _, err := url.ParseRequestURI(fg.DocumentationRoot); err != nil {
		newError := ValidationError{
			Tags:    []string{"DOCUMENTATION_ROOT"},
			Policy:  "A is URL",
			Message: "Documentation root must be a valid url.",
		}
		errors = append(errors, newError)
	}

	return errors

}
