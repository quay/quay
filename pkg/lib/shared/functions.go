package shared

import "fmt"

// FixInterface converts a map[interface{}]interface{} into a map[string]interface{}
func FixInterface(input map[interface{}]interface{}) map[string]interface{} {
	output := make(map[string]interface{})
	for key, value := range input {
		strKey := fmt.Sprintf("%v", key)
		output[strKey] = value
	}
	return output
}
