package validation

import (
	"fmt"
	"io/ioutil"

	"github.com/quay/config-tool/pkg/lib/config"
	"gopkg.in/yaml.v2"
)

// ValidateConf validates a config.yaml
func ValidateConf(configPath string) (config.Config, error) {

	// Read config file
	configBytes, err := ioutil.ReadFile(configPath)
	if err != nil {
		return config.Config{}, err
	}

	// Load config into struct
	var c map[string]interface{}
	if err = yaml.Unmarshal(configBytes, &c); err != nil {
		fmt.Println("failed")
	}

	// Create field groups
	configFieldGroups, err := config.NewConfig(c)
	if err != nil {
		return config.Config{}, err
	}

	return configFieldGroups, nil

}
