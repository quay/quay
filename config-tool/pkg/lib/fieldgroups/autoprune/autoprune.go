package autoprune

import (
	"errors"

	"github.com/creasty/defaults"
)

type AutoPruneFieldGroup struct {
	FEATURE_AUTO_PRUNE                 bool                          `default:"false" validate:"" json:"FEATURE_AUTO_PRUNE,omitempty" yaml:"FEATURE_AUTO_PRUNE,omitempty"`
	DEFAULT_NAMESPACE_AUTOPRUNE_POLICY *DefaultAutoPrunePolicyStruct `default:"" validate:"" json:"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY,omitempty" yaml:"DEFAULT_NAMESPACE_AUTOPRUNE_POLICY,omitempty"`
}

type DefaultAutoPrunePolicyStruct struct {
	Method string `default:"" validate:"" json:"method,omitempty" yaml:"method,omitempty"`
	// value can be string or int
	Value interface{} `default:"" validate:"" json:"value,omitempty" yaml:"value,omitempty"`
}

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

	if value, ok := fullConfig["DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"]; ok {
		var err error
		value := value.(map[string]interface{})
		newAutoPruneFieldGroup.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY, err = NewDefaultOrgAutoPrunePolicyStruct(value)
		if err != nil {
			return newAutoPruneFieldGroup, err
		}
	}

	return newAutoPruneFieldGroup, nil
}

func NewDefaultOrgAutoPrunePolicyStruct(defaultConfig map[string]interface{}) (*DefaultAutoPrunePolicyStruct, error) {
	newDefaultOrgAutoPrunePolicyStruct := &DefaultAutoPrunePolicyStruct{}
	defaults.Set(newDefaultOrgAutoPrunePolicyStruct)

	if value, ok := defaultConfig["method"]; ok {
		newDefaultOrgAutoPrunePolicyStruct.Method, ok = value.(string)
		if !ok {
			return newDefaultOrgAutoPrunePolicyStruct, errors.New("DEFAULT_NAMESPACE_AUTOPRUNE_POLICY `method` must be of type string")
		}
	}

	if value, ok := defaultConfig["value"]; ok {
		newDefaultOrgAutoPrunePolicyStruct.Value, ok = value.(int)
		if ok {
			return newDefaultOrgAutoPrunePolicyStruct, nil
		}
	}

	if value, ok := defaultConfig["value"]; ok {
		newDefaultOrgAutoPrunePolicyStruct.Value, ok = value.(string)
		if !ok {
			return newDefaultOrgAutoPrunePolicyStruct, errors.New("DEFAULT_NAMESPACE_AUTOPRUNE_POLICY `value` must be of type string or int")
		}
	}

	return newDefaultOrgAutoPrunePolicyStruct, nil
}
