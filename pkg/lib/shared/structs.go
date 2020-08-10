package shared

// Options is a struct that tells the validator how to validate
type Options struct {
	Mode         string // One of Online, Offline, Testing
	Certificates map[string][]byte
}

// ValidationError is a struct that holds information about a failed field group policy
type ValidationError struct {
	Tags    []string
	Policy  string
	Message string
}

func (ve ValidationError) String() string {
	return ve.Message
}
