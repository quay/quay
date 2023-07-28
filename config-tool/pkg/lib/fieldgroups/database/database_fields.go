package database

// Fields returns a list of strings representing the fields in this field group
func (fg *DatabaseFieldGroup) Fields() []string {
	return []string{"DB_CONNECTION_ARGS", "DB_URI"}
}
