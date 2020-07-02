package fieldgroups

import (
	"errors"
	"github.com/creasty/defaults"
)

// UserVisibleSettingsFieldGroup represents the UserVisibleSettingsFieldGroup config fields
type UserVisibleSettingsFieldGroup struct {
	AvatarKind               string          `default:"local" validate:""`
	Branding                 *BrandingStruct `default:"" validate:""`
	ContactInfo              []interface{}   `default:"[]" validate:""`
	RegistryTitle            string          `default:"Project Quay" validate:""`
	RegistryTitleShort       string          `default:"Project Quay" validate:""`
	SearchMaxResultPageCount int             `default:"10" validate:""`
	SearchResultsPerPage     int             `default:"10" validate:""`
}

// BrandingStruct represents the BrandingStruct config fields
type BrandingStruct struct {
	Logo      string `default:"/static/img/quay-horizontal-color.svg" validate:"url"`
	FooterImg string `default:"" validate:"url"`
	FooterUrl string `default:"" validate:"url"`
}

// NewUserVisibleSettingsFieldGroup creates a new UserVisibleSettingsFieldGroup
func NewUserVisibleSettingsFieldGroup(fullConfig map[string]interface{}) (FieldGroup, error) {
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
		value := fixInterface(value.(map[interface{}]interface{}))
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
