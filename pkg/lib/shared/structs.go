package shared

// ValidationError is a struct that holds information about a failed field group policy
type ValidationError struct {
	Tags    []string
	Policy  string
	Message string
}
