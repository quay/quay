package shared

import (
	"bytes"
	"encoding/json"
)

// IntOrString is an int that may be unmarshaled from either a JSON number
// literal, or a JSON string.
type IntOrString int

// UnmarshalJSON will unmarshal an array of bytes into this type
func (i *IntOrString) UnmarshalJSON(d []byte) error {
	var v int
	err := json.Unmarshal(bytes.Trim(d, `"`), &v)
	*i = IntOrString(v)
	return err
}
