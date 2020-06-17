package validation

import (
	"fmt"
	"io/ioutil"

	"github.com/quay/config-tool/pkg/lib/fieldgroups"
	"gopkg.in/yaml.v2"
)

// ValidateConf validates a config.yaml
func ValidateConf(configPath string) fieldgroups.Config {

	// Read config file
	configBytes, err := ioutil.ReadFile(configPath)
	if err != nil {
		fmt.Println(err.Error())
		return nil
	}

	// Load config into struct
	var c map[string]interface{}
	if err = yaml.Unmarshal(configBytes, &c); err != nil {
		fmt.Println("failed")
	}

	// Create field groups
	configFieldGroups := fieldgroups.NewConfig(c)

	return configFieldGroups

}
