package autoprune

import (
	"errors"
	"github.com/creasty/defaults"
)

type AutoPruneFieldGroup struct {
	FEATURE_AUTO_PRUNE           bool                   `default:"false" validate:"" json:"FEATURE_AUTO_PRUNE,omitempty" yaml:"FEATURE_AUTO_PRUNE,omitempty"`
	DEFAULT_ORG_AUTOPRUNE_POLICY map[string]interface{} `default:"" validate:"" json:"DEFAULT_ORG_AUTOPRUNE_POLICY,omitempty" yaml:"DEFAULT_ORG_AUTOPRUNE_POLICY,omitempty"`
}

// DefaultAutoPrunePolicyStruct represents the DefaultAutoPrunePolicy struct
type DefaultAutoPrunePolicyStruct map[string]interface{}

// NewAutoPruneFieldGroup creates a new AutoPruneFieldGroup
func NewAutoPruneFieldGroup(fullConfig map[string]interface{}) (*AutoPruneFieldGroup, error) {
	newAutoPruneFieldGroup := &AutoPruneFieldGroup{}
	defaults.Set(newAutoPruneFieldGroup)

	if value, ok := fullConfig["FEATURE_AUTO_PRUNE"]; ok {
		newAutoPruneFieldGroup.FEATURE_AUTO_PRUNE, ok = value.(bool)
		if !ok {
			return newAutoPruneFieldGroup, errors.New("FEATURE_AUTO_PRUNE must be of type bool")
		}
	}

	if value, ok := fullConfig["DEFAULT_ORG_AUTOPRUNE_POLICY"]; ok {

		var err error
		value := value.(map[string]interface{})
		newAutoPruneFieldGroup.DEFAULT_ORG_AUTOPRUNE_POLICY, err = NewDefaultOrgAutoPrunePolicyStruct(value)
		if err != nil {
			return newAutoPruneFieldGroup, err
		}
	}

	return newAutoPruneFieldGroup, nil
}

func NewDefaultOrgAutoPrunePolicyStruct(defaultConfig map[string]interface{}) (map[string]interface{}, error) {
	newDefaultOrgAutoPrunePolicyStruct := DefaultAutoPrunePolicyStruct{}
	for key, value := range defaultConfig {
		newDefaultOrgAutoPrunePolicyStruct[key] = value
	}
	return newDefaultOrgAutoPrunePolicyStruct, nil
}
