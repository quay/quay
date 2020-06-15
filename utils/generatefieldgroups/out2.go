package fieldgroups

// Struct Definition
type TagExpirationFieldGroup struct {
	FeatureChangeTagExpiration bool     `default:"false"`
	DefaultTagExpiration       string   `default:"2w"`
	TagExpirationOptions       []string `default:"[\"0s\", \"1d\", \"1w\", \"2w\", \"4w\"]"`
}

// Constructor
func NewTagExpirationFieldGroup(fullConfig map[string]interface{}) FieldGoup {
	newTagExpiration := &TagExpirationFieldGroup{}
	defaults.Set(newTagExpiration)

	if value, ok := fullConfig["FEATURE_CHANGE_TAG_EXPIRATION"]; ok {
		newTagExpiration.FeatureChangeTagExpiration = value
	}
	if value, ok := fullConfig["DEFAULT_TAG_EXPIRATION"]; ok {
		newTagExpiration.DefaultTagExpiration = value
	}
	if value, ok := fullConfig["TAG_EXPIRATION_OPTIONS"]; ok {
		newTagExpiration.TagExpirationOptions = value
	}

	return newTagExpiration
}

// Validator Function
func (fg *TagExpirationFieldGroup) Validate() (bool, error) {
	return true, nil
}
