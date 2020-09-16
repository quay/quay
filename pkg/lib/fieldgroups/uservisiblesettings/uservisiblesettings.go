package uservisiblesettings

import (
	"errors"

	"github.com/creasty/defaults"
)

// UserVisibleSettingsFieldGroup represents the UserVisibleSettingsFieldGroup config fields
type UserVisibleSettingsFieldGroup struct {
	AvatarKind               string          `default:"local" validate:"" json:"AVATAR_KIND" yaml:"AVATAR_KIND"`
	Branding                 *BrandingStruct `default:"" validate:"" json:"BRANDING" yaml:"BRANDING"`
	ContactInfo              []interface{}   `default:"[]" validate:"" json:"CONTACT_INFO" yaml:"CONTACT_INFO"`
	RegistryTitle            string          `default:"Project Quay" validate:"" json:"REGISTRY_TITLE" yaml:"REGISTRY_TITLE"`
	RegistryTitleShort       string          `default:"Project Quay" validate:"" json:"REGISTRY_TITLE_SHORT" yaml:"REGISTRY_TITLE_SHORT"`
	SearchMaxResultPageCount int             `default:"10" validate:"" json:"SEARCH_MAX_RESULT_PAGE_COUNT" yaml:"SEARCH_MAX_RESULT_PAGE_COUNT"`
	SearchResultsPerPage     int             `default:"10" validate:"" json:"SEARCH_RESULTS_PER_PAGE" yaml:"SEARCH_RESULTS_PER_PAGE"`
}

// BrandingStruct represents the BrandingStruct config fields
type BrandingStruct struct {
	Logo      string `default:"/static/img/quay-horizontal-color.svg" validate:"url" json:"logo" yaml:"logo"`
	FooterImg string `default:"" validate:"url" json:"footer_img" yaml:"footer_img"`
	FooterUrl string `default:"" validate:"url" json:"footer_url" yaml:"footer_url"`
}

// NewUserVisibleSettingsFieldGroup creates a new UserVisibleSettingsFieldGroup
func NewUserVisibleSettingsFieldGroup(fullConfig map[string]interface{}) (*UserVisibleSettingsFieldGroup, error) {
	newUserVisibleSettingsFieldGroup := &UserVisibleSettingsFieldGroup{}
	defaults.Set(newUserVisibleSettingsFieldGroup)

	if value, ok := fullConfig["AVATAR_KIND"]; ok {
		newUserVisibleSettingsFieldGroup.AvatarKind, ok = value.(string)
		if !ok {
			return newUserVisibleSettingsFieldGroup, errors.New("AVATAR_KIND must be of type string")
		}
	}
	if value, ok := fullConfig["BRANDING"]; ok {
		var err error
		value := value.(map[string]interface{})
		newUserVisibleSettingsFieldGroup.Branding, err = NewBrandingStruct(value)
		if err != nil {
			return newUserVisibleSettingsFieldGroup, err
		}
	}
	if value, ok := fullConfig["CONTACT_INFO"]; ok {
		newUserVisibleSettingsFieldGroup.ContactInfo, ok = value.([]interface{})
		if !ok {
			return newUserVisibleSettingsFieldGroup, errors.New("CONTACT_INFO must be of type []interface{}")
		}
	}
	if value, ok := fullConfig["REGISTRY_TITLE"]; ok {
		newUserVisibleSettingsFieldGroup.RegistryTitle, ok = value.(string)
		if !ok {
			return newUserVisibleSettingsFieldGroup, errors.New("REGISTRY_TITLE must be of type string")
		}
	}
	if value, ok := fullConfig["REGISTRY_TITLE_SHORT"]; ok {
		newUserVisibleSettingsFieldGroup.RegistryTitleShort, ok = value.(string)
		if !ok {
			return newUserVisibleSettingsFieldGroup, errors.New("REGISTRY_TITLE_SHORT must be of type string")
		}
	}
	if value, ok := fullConfig["SEARCH_MAX_RESULT_PAGE_COUNT"]; ok {
		newUserVisibleSettingsFieldGroup.SearchMaxResultPageCount, ok = value.(int)
		if !ok {
			return newUserVisibleSettingsFieldGroup, errors.New("SEARCH_MAX_RESULT_PAGE_COUNT must be of type int")
		}
	}
	if value, ok := fullConfig["SEARCH_RESULTS_PER_PAGE"]; ok {
		newUserVisibleSettingsFieldGroup.SearchResultsPerPage, ok = value.(int)
		if !ok {
			return newUserVisibleSettingsFieldGroup, errors.New("SEARCH_RESULTS_PER_PAGE must be of type int")
		}
	}

	return newUserVisibleSettingsFieldGroup, nil
}

// NewBrandingStruct creates a new BrandingStruct
func NewBrandingStruct(fullConfig map[string]interface{}) (*BrandingStruct, error) {
	newBrandingStruct := &BrandingStruct{}
	defaults.Set(newBrandingStruct)

	if value, ok := fullConfig["logo"]; ok {
		newBrandingStruct.Logo, ok = value.(string)
		if !ok {
			return newBrandingStruct, errors.New("logo must be of type string")
		}
	}
	if value, ok := fullConfig["footer_img"]; ok {
		newBrandingStruct.FooterImg, ok = value.(string)
		if !ok {
			return newBrandingStruct, errors.New("footer_img must be of type string")
		}
	}
	if value, ok := fullConfig["footer_url"]; ok {
		newBrandingStruct.FooterUrl, ok = value.(string)
		if !ok {
			return newBrandingStruct, errors.New("footer_url must be of type string")
		}
	}

	return newBrandingStruct, nil
}
