package lib

import (
	"context"
	"encoding/json"
	"io/ioutil"

	"github.com/qri-io/jsonschema"
	"gopkg.in/yaml.v2"
)

// ValidationResponse is a struct that holds the response data for a validation attempt
type ValidationResponse struct {
	IsValid   bool
	KeyErrors []jsonschema.KeyError
}

// ValidateSchema checks the config file against a JSON Schema Definition
func ValidateSchema(configPath, schemaPath string) (ValidationResponse, error) {

	// Read config file
	configBytes, err := ioutil.ReadFile(configPath)
	if err != nil {
		return ValidationResponse{}, err
	}

	// Load config into struct and convert to JSON
	var c interface{}
	if err = yaml.Unmarshal(configBytes, &c); err != nil {
		return ValidationResponse{}, err
	}
	c = YAMLtoJSON(c)
	config, err := json.Marshal(c)
	if err != nil {
		return ValidationResponse{}, err
	}

	// Read schema file
	schemaBytes, err := ioutil.ReadFile(schemaPath)
	if err != nil {
		return ValidationResponse{}, err
	}

	// Load schema file into struct
	rs := &jsonschema.Schema{}
	if err := json.Unmarshal(schemaBytes, rs); err != nil {
		return ValidationResponse{}, err
	}

	// Validate config against schema and get errors
	errs, err := rs.ValidateBytes(context.Background(), config)
	if err != nil {
		return ValidationResponse{}, err
	}

	// If schema errors exist
	if len(errs) > 0 {
		return ValidationResponse{IsValid: false, KeyErrors: errs}, nil
	}

	// No errors exist
	return ValidationResponse{IsValid: true, KeyErrors: nil}, nil

}

// YAMLtoJSON converts a YAML struct JSON
func YAMLtoJSON(i interface{}) interface{} {

	switch x := i.(type) {
	case map[interface{}]interface{}:
		m2 := map[string]interface{}{}
		for k, v := range x {
			m2[k.(string)] = YAMLtoJSON(v)
		}
		return m2
	case []interface{}:
		for i, v := range x {
			x[i] = YAMLtoJSON(v)
		}
	}
	return i
}
