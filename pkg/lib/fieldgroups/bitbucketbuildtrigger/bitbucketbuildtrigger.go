package bitbucketbuildtrigger

import (
	"errors"

	"github.com/creasty/defaults"
)

// BitbucketBuildTriggerFieldGroup represents the BitbucketBuildTriggerFieldGroup config fields
type BitbucketBuildTriggerFieldGroup struct {
	BitbucketTriggerConfig *BitbucketTriggerConfigStruct `default:"" validate:"" json:"BITBUCKET_TRIGGER_CONFIG,omitempty" yaml:"BITBUCKET_TRIGGER_CONFIG,omitempty"`
	FeatureBitbucketBuild  bool                          `default:"false" validate:"" json:"FEATURE_BITBUCKET_BUILD,omitempty" yaml:"FEATURE_BITBUCKET_BUILD,omitempty"`
	FeatureBuildSupport    bool                          `default:"" validate:"" json:"FEATURE_BUILD_SUPPORT,omitempty" yaml:"FEATURE_BUILD_SUPPORT,omitempty"`
}

// BitbucketTriggerConfigStruct represents the BitbucketTriggerConfigStruct config fields
type BitbucketTriggerConfigStruct struct {
	ConsumerKey    string `default:"" validate:"" json:"CONSUMER_KEY,omitempty" yaml:"CONSUMER_KEY,omitempty"`
	ConsumerSecret string `default:"" validate:"" json:"CONSUMER_SECRET,omitempty" yaml:"CONSUMER_SECRET,omitempty"`
}

// NewBitbucketBuildTriggerFieldGroup creates a new BitbucketBuildTriggerFieldGroup
func NewBitbucketBuildTriggerFieldGroup(fullConfig map[string]interface{}) (*BitbucketBuildTriggerFieldGroup, error) {
	newBitbucketBuildTriggerFieldGroup := &BitbucketBuildTriggerFieldGroup{}
	defaults.Set(newBitbucketBuildTriggerFieldGroup)

	if value, ok := fullConfig["BITBUCKET_TRIGGER_CONFIG"]; ok {
		var err error
		value := value.(map[string]interface{})
		newBitbucketBuildTriggerFieldGroup.BitbucketTriggerConfig, err = NewBitbucketTriggerConfigStruct(value)
		if err != nil {
			return newBitbucketBuildTriggerFieldGroup, err
		}
	}
	if value, ok := fullConfig["FEATURE_BITBUCKET_BUILD"]; ok {
		newBitbucketBuildTriggerFieldGroup.FeatureBitbucketBuild, ok = value.(bool)
		if !ok {
			return newBitbucketBuildTriggerFieldGroup, errors.New("FEATURE_BITBUCKET_BUILD must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_BUILD_SUPPORT"]; ok {
		newBitbucketBuildTriggerFieldGroup.FeatureBuildSupport, ok = value.(bool)
		if !ok {
			return newBitbucketBuildTriggerFieldGroup, errors.New("FEATURE_BUILD_SUPPORT must be of type bool")
		}
	}

	return newBitbucketBuildTriggerFieldGroup, nil
}

// NewBitbucketTriggerConfigStruct creates a new BitbucketTriggerConfigStruct
func NewBitbucketTriggerConfigStruct(fullConfig map[string]interface{}) (*BitbucketTriggerConfigStruct, error) {
	newBitbucketTriggerConfigStruct := &BitbucketTriggerConfigStruct{}
	defaults.Set(newBitbucketTriggerConfigStruct)

	if value, ok := fullConfig["CONSUMER_KEY"]; ok {
		newBitbucketTriggerConfigStruct.ConsumerKey, ok = value.(string)
		if !ok {
			return newBitbucketTriggerConfigStruct, errors.New("CONSUMER_KEY must be of type string")
		}
	}
	if value, ok := fullConfig["CONSUMER_SECRET"]; ok {
		newBitbucketTriggerConfigStruct.ConsumerSecret, ok = value.(string)
		if !ok {
			return newBitbucketTriggerConfigStruct, errors.New("CONSUMER_SECRET must be of type string")
		}
	}

	return newBitbucketTriggerConfigStruct, nil
}
