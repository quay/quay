package lib

// TagExpirationFieldGroup is a FieldGroup representing the Tag Expiration settings
type TagExpirationFieldGroup struct {

	// Whether users and organizations are allowed to change the tag expiration for
	// tags in their namespace. Defaults to True.
	FeatureChangeTagExpiration bool `yaml:"FEATURE_CHANGE_TAG_EXPIRATION"`

	// The default, configurable tag expiration time for time machine. Defaults to
	// `2w`.
	DefaultTagExpiration string `yaml:"DEFAULT_TAG_EXPIRATION"`

	// The options that users can select for expiration of tags in their namespace (if enabled)
	TagExpirationOptions []string `yaml:"TAG_EXPIRATION_OPTIONS"`
}

// Validate assures that the field group contains valid settings
func (fg *TagExpirationFieldGroup) Validate() (bool, error) {
	return true, nil
}
