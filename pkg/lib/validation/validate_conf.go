package validation

// import (
// 	"io/ioutil"

// 	"github.com/quay/config-tool/pkg/lib/config"
// 	"github.com/quay/config-tool/pkg/lib/shared"
// 	"gopkg.in/yaml.v2"
// )

// // ValidateConf validates a config.yaml
// func ValidateConf(configDir string) (config.Config, error) {

// 	// Read config file
// 	configBytes, err := ioutil.ReadFile(configDir)
// 	if err != nil {
// 		return config.Config{}, err
// 	}

// 	// Load config into struct
// 	var c map[string]interface{}
// 	if err = yaml.Unmarshal(configBytes, &c); err != nil {
// 		return config.Config{}, err
// 	}

// 	// Create field groups
// 	configFieldGroups, err := config.NewConfig(c)
// 	if err != nil {
// 		return config.Config{}, err
// 	}

// 	certs := shared.LoadCerts(configDir)
// 	opts := shared.Options{
// 		Mode:         "online",
// 		Certificates: certs,
// 	}

// 	errors := configFieldGroups.Validate(opts)

// 	return configFieldGroups, nil

// }
