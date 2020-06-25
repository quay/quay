package fieldgroups

import (
	"regexp"

	"github.com/go-playground/validator/v10"
)

// customValidate validates that a field has the correct pattern
func customValidateTimePattern(fl validator.FieldLevel) bool {

	re := regexp.MustCompile(`^[0-9]+(w|m|d|h|s)$`)
	matches := re.FindAllString(fl.Field().String(), -1)

	if len(matches) != 1 {
		return false
	}

	return true

}

// customValidateFoundInStorage validates that the current field is found in distributed storage config
func customValidateFoundInStorage(fl validator.FieldLevel) bool {

	// By default, assume it is not present
	present := false

	// Get storage location
	storageLocation := fl.Field().String()

	// Get distributed storage
	distributedStorageConfigValue, _, _, ok := fl.GetStructFieldOKAdvanced2(fl.Parent(), "DistributedStorageConfig")

	// If it could not find this field
	if !ok {
		return false
	}

	// Convert value to proper type and search keys
	distributedStorageConfig, ok := distributedStorageConfigValue.Interface().(DistributedStorageConfigStruct)
	if !ok {
		return false
	}

	for key := range distributedStorageConfig {
		if storageLocation == key {
			present = true
		}
	}

	return present

}
