package fieldgroups

import "fmt"

// FieldGroup is an interface that implements the Validate() function
type FieldGroup interface {
	Validate() []ValidationError
}

// Validation is a struct that holds information about a failed field group policy
type ValidationError struct {
	Tags    []string
	Policy  string
	Message string
}

// Config is a struct that represents a configuration as a mapping of field groups
type Config map[string]FieldGroup

// NewConfig creates a Config struct from a map[string]interface{}
func NewConfig(fullConfig map[string]interface{}) (Config, error) {

	var err error
	newConfig := Config{}
	newActionLogArchivingFieldGroup, err := NewActionLogArchivingFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["ActionLogArchiving"] = newActionLogArchivingFieldGroup
	newAppTokenAuthenticationFieldGroup, err := NewAppTokenAuthenticationFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["AppTokenAuthentication"] = newAppTokenAuthenticationFieldGroup
	newUserVisibleSettingsFieldGroup, err := NewUserVisibleSettingsFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["UserVisibleSettings"] = newUserVisibleSettingsFieldGroup
	newDatabaseFieldGroup, err := NewDatabaseFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["Database"] = newDatabaseFieldGroup
	newSecurityScannerFieldGroup, err := NewSecurityScannerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["SecurityScanner"] = newSecurityScannerFieldGroup
	newElasticSearchFieldGroup, err := NewElasticSearchFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["ElasticSearch"] = newElasticSearchFieldGroup
	newBitbucketBuildTriggerFieldGroup, err := NewBitbucketBuildTriggerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["BitbucketBuildTrigger"] = newBitbucketBuildTriggerFieldGroup
	newDocumentationFieldGroup, err := NewDocumentationFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["Documentation"] = newDocumentationFieldGroup
	newAccessSettingsFieldGroup, err := NewAccessSettingsFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["AccessSettings"] = newAccessSettingsFieldGroup
	newTeamSyncingFieldGroup, err := NewTeamSyncingFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["TeamSyncing"] = newTeamSyncingFieldGroup

	return newConfig, nil
}

// fixInterface converts a map[interface{}]interface{} into a map[string]interface{}
func fixInterface(input map[interface{}]interface{}) map[string]interface{} {
	output := make(map[string]interface{})
	for key, value := range input {
		strKey := fmt.Sprintf("%v", key)
		output[strKey] = value
	}
	return output
}
