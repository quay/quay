package shared

// Options is a struct that tells the validator how to validate
type Options struct {
	ConfigDir string
}

// ValidationError is a struct that holds information about a failed field group policy
type ValidationError struct {
	Tags    []string
	Policy  string
	Message string
}
