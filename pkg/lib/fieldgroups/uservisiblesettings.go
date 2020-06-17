package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// UserVisibleSettingsFieldGroup represents the UserVisibleSettings config fields
type UserVisibleSettingsFieldGroup struct {
	RegistryTitle            string        `default:"Project Quay" validate:""`
	RegistryTitleShort       string        `default:"Project Quay" validate:""`
	SearchResultsPerPage     int           `default:"10" validate:""`
	SearchMaxResultPageCount int           `default:"10" validate:""`
	ContactInfo              []interface{} `default:"[]" validate:""`
	AvatarKind               string        `default:"local" validate:"oneof=local gravatar"`
	Branding                 struct {
		Logo       string `default:"" validate:"url"`
		FooterIMG  string `default:"" validate:"url"`
		FooterURL  string `default:"" validate:"url"`
		TestNested struct {
			TestNested2 string `default:"" validate:""`
		}
	}
}

// NewUserVisibleSettingsFieldGroup creates a new UserVisibleSettingsFieldGroup
func NewUserVisibleSettingsFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newUserVisibleSettings := &UserVisibleSettingsFieldGroup{}
	defaults.Set(newUserVisibleSettings)

	if value, ok := fullConfig["REGISTRY_TITLE"]; ok {
		newUserVisibleSettings.RegistryTitle = value.(string)
	}
	if value, ok := fullConfig["REGISTRY_TITLE_SHORT"]; ok {
		newUserVisibleSettings.RegistryTitleShort = value.(string)
	}
	if value, ok := fullConfig["SEARCH_RESULTS_PER_PAGE"]; ok {
		newUserVisibleSettings.SearchResultsPerPage = value.(int)
	}
	if value, ok := fullConfig["SEARCH_MAX_RESULT_PAGE_COUNT"]; ok {
		newUserVisibleSettings.SearchMaxResultPageCount = value.(int)
	}
	if value, ok := fullConfig["CONTACT_INFO"]; ok {
		newUserVisibleSettings.ContactInfo = value.([]interface{})
	}
	if value, ok := fullConfig["AVATAR_KIND"]; ok {
		newUserVisibleSettings.AvatarKind = value.(string)
	}
	if value, ok := fullConfig["BRANDING"]; ok {
		newUserVisibleSettings.Branding = value.(object)
	}

	return newUserVisibleSettings
}

// Validate checks the configuration settings for this field group
func (fg *UserVisibleSettingsFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()
	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
