package validation

import (
	"fmt"
	"io/ioutil"

	"github.com/quay/config-tool/pkg/lib/fieldgroups"
	"gopkg.in/yaml.v2"
)

// ValidateConf validates a config.yaml
func ValidateConf(configPath string) (fieldgroups.Config, error) {

	// Read config file
	configBytes, err := ioutil.ReadFile(configPath)
	if err != nil {
		return fieldgroups.Config{}, err
	}

	// Load config into struct
	var c map[string]interface{}
	if err = yaml.Unmarshal(configBytes, &c); err != nil {
		fmt.Println("failed")
	}

	// Create field groups
	configFieldGroups, err := fieldgroups.NewConfig(c)
	if err != nil {
		return fieldgroups.Config{}, err
	}

	return configFieldGroups, nil

}
