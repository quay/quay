package lib

// FieldGroup is an interface that implements the Validate metohd
type FieldGroup interface {
	Validate() (bool, error)
}
