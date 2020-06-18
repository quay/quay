package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// UserVisibleSettingsFieldGroup represents the UserVisibleSettingsFieldGroup config fields
type UserVisibleSettingsFieldGroup struct {
	RegistryTitle            string        `default:"Project Quay" validate:""`
	RegistryTitleShort       string        `default:"Project Quay" validate:""`
	SearchResultsPerPage     int           `default:"10" validate:""`
	SearchMaxResultPageCount int           `default:"10" validate:""`
	ContactInfo              []interface{} `default:"[]" validate:""`
	AvatarKind               string        `default:"local" validate:"oneof=local gravatar"`
	Branding                 *BrandingStruct
}

// BrandingStruct represents the BrandingStruct config fields
type BrandingStruct struct {
	Logo      string `default:"" validate:"url"`
	FooterIMG string `default:"" validate:"url"`
	FooterURL string `default:"" validate:"url"`
}

// NewUserVisibleSettingsFieldGroup creates a new UserVisibleSettingsFieldGroup
func NewUserVisibleSettingsFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newUserVisibleSettingsFieldGroup := &UserVisibleSettingsFieldGroup{}
	defaults.Set(newUserVisibleSettingsFieldGroup)

	if value, ok := fullConfig["REGISTRY_TITLE"]; ok {
		newUserVisibleSettingsFieldGroup.RegistryTitle = value.(string)
	}
	if value, ok := fullConfig["REGISTRY_TITLE_SHORT"]; ok {
		newUserVisibleSettingsFieldGroup.RegistryTitleShort = value.(string)
	}
	if value, ok := fullConfig["SEARCH_RESULTS_PER_PAGE"]; ok {
		newUserVisibleSettingsFieldGroup.SearchResultsPerPage = value.(int)
	}
	if value, ok := fullConfig["SEARCH_MAX_RESULT_PAGE_COUNT"]; ok {
		newUserVisibleSettingsFieldGroup.SearchMaxResultPageCount = value.(int)
	}
	if value, ok := fullConfig["CONTACT_INFO"]; ok {
		newUserVisibleSettingsFieldGroup.ContactInfo = value.([]interface{})
	}
	if value, ok := fullConfig["AVATAR_KIND"]; ok {
		newUserVisibleSettingsFieldGroup.AvatarKind = value.(string)
	}
	if value, ok := fullConfig["BRANDING"]; ok {
		newUserVisibleSettingsFieldGroup.Branding = NewBrandingStruct(value.(map[string]interface{}))
	}

	return newUserVisibleSettingsFieldGroup
}

// NewBrandingStruct creates a new BrandingStruct
func NewBrandingStruct(fullConfig map[string]interface{}) *BrandingStruct {
	newBrandingStruct := &BrandingStruct{}
	defaults.Set(newBrandingStruct)

	if value, ok := fullConfig["logo"]; ok {
		newBrandingStruct.Logo = value.(string)
	}
	if value, ok := fullConfig["footer_img"]; ok {
		newBrandingStruct.FooterIMG = value.(string)
	}
	if value, ok := fullConfig["footer_url"]; ok {
		newBrandingStruct.FooterURL = value.(string)
	}

	return newBrandingStruct
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
