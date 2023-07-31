package uservisiblesettings

// Fields returns a list of strings representing the fields in this field group
func (fg *UserVisibleSettingsFieldGroup) Fields() []string {
	return []string{"AVATAR_KIND", "BRANDING", "CONTACT_INFO", "REGISTRY_TITLE", "REGISTRY_TITLE_SHORT", "SEARCH_MAX_RESULT_PAGE_COUNT", "SEARCH_RESULTS_PER_PAGE"}
}
