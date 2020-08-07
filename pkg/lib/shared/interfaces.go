package shared

// FieldGroup is an interface that implements the Validate() function
type FieldGroup interface {
	Validate(opts Options) []ValidationError
	Fields() []string
}
