package elasticsearch

// Fields returns a list of strings representing the fields in this field group
func (fg *ElasticSearchFieldGroup) Fields() []string {
	return []string{"LOGS_MODEL", "LOGS_MODEL_CONFIG"}
}
