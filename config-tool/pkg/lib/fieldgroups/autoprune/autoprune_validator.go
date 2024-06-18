package autoprune

import (
	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// Validate checks the configuration settings for this field group
func (fg *AutoPruneFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	fgName := "AutoPrune"

	// Make empty errors
	errors := []shared.ValidationError{}

	// If false, skip validation
	if fg.FEATURE_AUTO_PRUNE == false {
		return errors
	}

	// If npt present, skip validation
	if fg.DEFAULT_ORG_AUTOPRUNE_POLICY == nil {
		return errors
	}

	if ok, err := shared.ValidateDefaultAutoPruneKey(fg.DEFAULT_ORG_AUTOPRUNE_POLICY, "DEFAULT_ORG_AUTOPRUNE_POLICY", fgName); !ok {
		errors = append(errors, err)
	}

	return errors
}
