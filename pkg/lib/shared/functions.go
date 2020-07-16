package shared

import (
	"fmt"
	"reflect"
)

// FixInterface converts a map[interface{}]interface{} into a map[string]interface{}
func FixInterface(input map[interface{}]interface{}) map[string]interface{} {
	output := make(map[string]interface{})
	for key, value := range input {
		strKey := fmt.Sprintf("%v", key)
		output[strKey] = value
	}
	return output
}

// GetFields will return the list of YAML fields in a given field group
func GetFields(fg FieldGroup) []string {

	var fieldNames []string

	// get type
	t := reflect.Indirect(reflect.ValueOf(fg)).Type()

	// Iterate over all available fields and read the tag value
	for i := 0; i < t.NumField(); i++ {
		// Get the field, returns https://golang.org/pkg/reflect/#StructField
		field := t.Field(i)

		// Get the field tag value
		yaml := field.Tag.Get("yaml")

		fieldNames = append(fieldNames, yaml)

	}

	return fieldNames
}
