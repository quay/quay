package fieldgroups

import (
	"errors"
	"github.com/creasty/defaults"
)

// BitbucketBuildTriggerFieldGroup represents the BitbucketBuildTriggerFieldGroup config fields
type BitbucketBuildTriggerFieldGroup struct {
	BitbucketTriggerConfig *BitbucketTriggerConfigStruct `default:"" validate:""`
	FeatureBitbucketBuild  bool                          `default:"false" validate:""`
	FeatureBuildSupport    bool                          `default:"" validate:""`
}

// BitbucketTriggerConfigStruct represents the BitbucketTriggerConfigStruct config fields
type BitbucketTriggerConfigStruct struct {
	ConsumerSecret string `default:"" validate:""`
	ConsumerKey    string `default:"" validate:""`
}

// NewBitbucketBuildTriggerFieldGroup creates a new BitbucketBuildTriggerFieldGroup
func NewBitbucketBuildTriggerFieldGroup(fullConfig map[string]interface{}) (FieldGroup, error) {
	newBitbucketBuildTriggerFieldGroup := &BitbucketBuildTriggerFieldGroup{}
	defaults.Set(newBitbucketBuildTriggerFieldGroup)

	if value, ok := fullConfig["BITBUCKET_TRIGGER_CONFIG"]; ok {
		var err error
		value := fixInterface(value.(map[interface{}]interface{}))
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

	if value, ok := fullConfig["CONSUMER_SECRET"]; ok {
		newBitbucketTriggerConfigStruct.ConsumerSecret, ok = value.(string)
		if !ok {
			return newBitbucketTriggerConfigStruct, errors.New("CONSUMER_SECRET must be of type string")
		}
	}
	if value, ok := fullConfig["CONSUMER_KEY"]; ok {
		newBitbucketTriggerConfigStruct.ConsumerKey, ok = value.(string)
		if !ok {
			return newBitbucketTriggerConfigStruct, errors.New("CONSUMER_KEY must be of type string")
		}
	}

	return newBitbucketTriggerConfigStruct, nil
}
