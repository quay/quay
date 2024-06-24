package autoprune

// Fields returns a list of strings representing the fields in this field group
func (fg *AutoPruneFieldGroup) Fields() []string {
	return []string{"FEATURE_AUTO_PRUNE", "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"}
}
