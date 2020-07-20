package signingengine

// Fields returns a list of strings representing the fields in this field group
func (fg *SigningEngineFieldGroup) Fields() []string {
	return []string{"GPG2_PRIVATE_KEY_FILENAME", "GPG2_PRIVATE_KEY_NAME", "GPG2_PUBLIC_KEY_FILENAME", "SIGNING_ENGINE"}
}
