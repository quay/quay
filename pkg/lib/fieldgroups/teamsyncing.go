package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// TeamSyncingFieldGroup represents the TeamSyncingFieldGroup config fields
type TeamSyncingFieldGroup struct {
	TeamResyncStaleTime                 string `default:"30m" validate:"customValidateTimePattern"`
	FeatureNonsuperuserTeamSyncingSetup bool   `default:"false" validate:""`
	FeatureTeamSyncing                  bool   `default:"false" validate:""`
}

// NewTeamSyncingFieldGroup creates a new TeamSyncingFieldGroup
func NewTeamSyncingFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newTeamSyncingFieldGroup := &TeamSyncingFieldGroup{}
	defaults.Set(newTeamSyncingFieldGroup)

	if value, ok := fullConfig["TEAM_RESYNC_STALE_TIME"]; ok {
		newTeamSyncingFieldGroup.TeamResyncStaleTime = value.(string)
	}
	if value, ok := fullConfig["FEATURE_NONSUPERUSER_TEAM_SYNCING_SETUP"]; ok {
		newTeamSyncingFieldGroup.FeatureNonsuperuserTeamSyncingSetup = value.(bool)
	}
	if value, ok := fullConfig["FEATURE_TEAM_SYNCING"]; ok {
		newTeamSyncingFieldGroup.FeatureTeamSyncing = value.(bool)
	}

	return newTeamSyncingFieldGroup
}

// Validate checks the configuration settings for this field group
func (fg *TeamSyncingFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()

	validate.RegisterValidation("customValidateTimePattern", customValidateTimePattern)

	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
