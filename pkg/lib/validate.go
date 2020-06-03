package lib

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"

	"github.com/qri-io/jsonschema"
	"gopkg.in/yaml.v2"
)

// ValidateSchema checks the config file against a JSON Schema Definition
func ValidateSchema(configPath, schemaPath string) (bool, error) {

	// Read config file
	configBytes, err := ioutil.ReadFile(configPath)
	if err != nil {
		return false, err
	}

	// Load config into struct and convert to JSON
	var c interface{}
	if err = yaml.Unmarshal(configBytes, &c); err != nil {
		return false, err
	}
	c = YAMLtoJSON(c)
	config, err := json.Marshal(c)
	if err != nil {
		return false, err
	}

	// Read schema file
	schemaBytes, err := ioutil.ReadFile(schemaPath)
	if err != nil {
		return false, err
	}

	// Load schema file into struct
	rs := &jsonschema.Schema{}
	if err := json.Unmarshal(schemaBytes, rs); err != nil {
		return false, err
	}

	// Validate config against schema and get errors
	errs, err := rs.ValidateBytes(context.Background(), config)
	if err != nil {
		return false, err
	}
	if len(errs) > 0 {
		for i, err := range errs {
			fmt.Println(i, err)
		}
		return false, nil
	}

	// Scheme validation was successful
	return true, nil
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
