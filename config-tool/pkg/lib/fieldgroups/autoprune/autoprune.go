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
	Policies []*AutoPrunePolicy `default:"" validate:"" json:"policies,omitempty" yaml:"policies,omitempty"`
}

type AutoPrunePolicy struct {
	Method string      `default:"" validate:"required" json:"method,omitempty" yaml:"method,omitempty"`
	Value  interface{} `default:"" validate:"required" json:"value,omitempty" yaml:"value,omitempty"`
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
		policies, ok := value.([]interface{})
		if !ok {
			return newAutoPruneFieldGroup, errors.New("DEFAULT_NAMESPACE_AUTOPRUNE_POLICY must be a list of policies")
		}

		newAutoPruneFieldGroup.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY = &DefaultAutoPrunePolicyStruct{}
		newAutoPruneFieldGroup.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Policies = make([]*AutoPrunePolicy, 0, len(policies))

		for _, policy := range policies {
			policyConfig, ok := policy.(map[string]interface{})
			if !ok {
				return newAutoPruneFieldGroup, errors.New("each policy in DEFAULT_NAMESPACE_AUTOPRUNE_POLICY must be a map")
			}

			autoPrunePolicy, err := NewAutoPrunePolicy(policyConfig)
			if err != nil {
				return newAutoPruneFieldGroup, err
			}

			newAutoPruneFieldGroup.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Policies = append(newAutoPruneFieldGroup.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY.Policies, autoPrunePolicy)
		}
	}

	return newAutoPruneFieldGroup, nil
}

func NewAutoPrunePolicy(policyConfig map[string]interface{}) (*AutoPrunePolicy, error) {
	autoPrunePolicy := &AutoPrunePolicy{}
	defaults.Set(autoPrunePolicy)

	if value, ok := policyConfig["method"]; ok {
		autoPrunePolicy.Method, ok = value.(string)
		if !ok {
			return autoPrunePolicy, errors.New("method must be a string")
		}
	} else {
		return autoPrunePolicy, errors.New("method is required")
	}

	if value, ok := policyConfig["value"]; ok {
		autoPrunePolicy.Value = value // No type checking needed here because Value is interface{}
	} else {
		return autoPrunePolicy, errors.New("value is required")
	}

	return autoPrunePolicy, nil
}
