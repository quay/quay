package autoprune

import (
	"regexp"

	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *AutoPruneFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "AutoPrune"

	// Make empty errors
	errors := []shared.ValidationError{}

	// If FEATURE_AUTO_PRUNE is false, skip validation
	if fg.FEATURE_AUTO_PRUNE == false {
		return errors
	}

	// If DEFAULT_NAMESPACE_AUTOPRUNE_POLICY is not present, skip validation
	if fg.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY == nil {
		return errors
	}

	// Check for method key
	if ok, err := shared.ValidateDefaultAutoPruneKey(fg.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Method, "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY", fgName); !ok {
		errors = append(errors, err)
	}

	// Make sure the key `value` exists
	if fg.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Value == nil {
		newError := shared.ValidationError{
			Tags:       []string{"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"},
			FieldGroup: fgName,
			Message:    "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY must have the key `value`",
		}
		errors = append(errors, newError)
		return errors
	}

	// number_of_tags method requires value to be `int`
	if fg.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Method == "number_of_tags" {
		value, ok := fg.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Value.(int)
		if !ok {
			newError := shared.ValidationError{
				Tags:       []string{"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"},
				FieldGroup: fgName,
				Message:    "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY method `number_of_tags` must have an integer value",
			}
			errors = append(errors, newError)
			return errors
		}
		if value < 1 {
			newError := shared.ValidationError{
				Tags:       []string{"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"},
				FieldGroup: fgName,
				Message:    "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY method `number_of_tags` must have an integer value more than 0",
			}
			errors = append(errors, newError)
			return errors
		}
	}

	// creation_date method requires value to be `string`
	if fg.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Method == "creation_date" {
		value, ok := fg.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Value.(string)
		if !ok {
			newError := shared.ValidationError{
				Tags:       []string{"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"},
				FieldGroup: fgName,
				Message:    "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY method `creation_date` must have a string type as value",
			}
			errors = append(errors, newError)
			return errors
		} else {
			// creation_date value be int followed by one of s,m,d,w,y
			re, _ := regexp.Compile(`^([0-9]+[smdwy])$`)
			if !re.MatchString(value) {
				newError := shared.ValidationError{
					Tags:       []string{"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"},
					FieldGroup: fgName,
					Message:    "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY creation_date value must follow: `^([0-9]+[smdwy])$`",
				}
				errors = append(errors, newError)
				return errors
			}
		}
	}

	return errors
}
