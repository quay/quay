# Creating Custom Config Definition

By default, this tool generates a validator executable for Quay. However, one also has the option to define a custom Config definition.

## Design:

A Config definiton is a list of `FieldGroup`'s which contain metadata regarding a config.yaml field. This includes the field name, type, default, and validation flags. The definition will follow the following schema:

```json
{
  "fieldGroupOne": [
    {
      "name": "attributeOne",
      "type": "string",
      "yaml": "ATTRIBUTE_ONE",
      "default": "",
      "validate": "required"
    },
    {
      "name": "attributeTwo",
      "type": "interface{}",
      "yaml": "ATTRIBUTE_TWO",
      "default": "",
      "validate": "required",
      "properties": [
        {
          "name": "attributeThree",
          "type": "string",
          "yaml": "ATTRIBUTE_THREE",
          "default": "",
          "validate": "required"
        }
      ]
    }
  ],
  "fieldGroupTwo": [
    {
      "name": "attributeFour",
      "type": "string",
      "yaml": "ATTRIBUTE_FOUR",
      "default": "",
      "validate": "required"
    }
  ]
}
```

For each field group, a file will be made that includes struct definitions and constructors for the group and nested subfields. A `config.go` file will also be created. This will be an object that holds all of your field group structs in a map.

## Usage

To create your own config validator, you only need to follow two simple steps.

1. Edit the `fieldgroups.json` file in this folder to match your desired Config definition.

2. Run `make all` from the home directory

3. Run `config-tool validate -c <path-to-config>` to see your new validator

4. Import field group structs from the `fieldgroups` package into any external project if desired

## Example

To show an example of how one can create their a validator from their own Config definition, we will go through how the `SecurityScannerFieldGroup` was implemented in the Quay validator:

1. Edit `fieldgroups.json` to the following

```json
{
  "SecurityScannerFieldGroup": [
    {
      "name": "FeatureSecurityScanner",
      "yaml": "FEATURE_SECURITY_SCANNER",
      "type": "bool",
      "default": "false",
      "validate": "omitempty"
    },
    {
      "name": "FeatureSecurityNotifications",
      "yaml": "FEATURE_SECURITY_NOTIFICATIONS",
      "type": "bool",
      "default": "false",
      "validate": "omitempty"
    },
    {
      "name": "SecurityScannerEndpoint",
      "yaml": "SECURITY_SCANNER_ENDPOINT",
      "type": "string",
      "default": "",
      "validate": "required_with=FeatureSecurityScanner"
    }
  ]
}
```

2. Run `make clean generate`

   This will remove all previously generated field groups and repopulate the fieldgroups package with your new code. If you look in the fieldgroups package, you will notice that the file `securityscannerfieldgroup.go` has been created.

```go
package fieldgroups

import (
	"github.com/creasty/defaults"
	"github.com/go-playground/validator/v10"
)

// SecurityScannerFieldGroup represents the SecurityScannerFieldGroup config fields
type SecurityScannerFieldGroup struct {
	FeatureSecurityScanner       bool   `default:"false" validate:"omitempty"`
	FeatureSecurityNotifications bool   `default:"false" validate:"omitempty"`
	SecurityScannerEndpoint      string `default:"" validate:"required_with=FeatureSecurityScanner"`
}

// NewSecurityScannerFieldGroup creates a new SecurityScannerFieldGroup
func NewSecurityScannerFieldGroup(fullConfig map[string]interface{}) FieldGroup {
	newSecurityScannerFieldGroup := &SecurityScannerFieldGroup{}
	defaults.Set(newSecurityScannerFieldGroup)

	if value, ok := fullConfig["FEATURE_SECURITY_SCANNER"]; ok {
		newSecurityScannerFieldGroup.FeatureSecurityScanner = value.(bool)
	}
	if value, ok := fullConfig["FEATURE_SECURITY_NOTIFICATIONS"]; ok {
		newSecurityScannerFieldGroup.FeatureSecurityNotifications = value.(bool)
	}
	if value, ok := fullConfig["SECURITY_SCANNER_ENDPOINT"]; ok {
		newSecurityScannerFieldGroup.SecurityScannerEndpoint = value.(string)
	}

	return newSecurityScannerFieldGroup
}

// Validate checks the configuration settings for this field group
func (fg *SecurityScannerFieldGroup) Validate() validator.ValidationErrors {
	validate := validator.New()
	err := validate.Struct(fg)
	if err == nil {
		return nil
	}
	validationErrors := err.(validator.ValidationErrors)
	return validationErrors
}
```

This generated file contains our constructors, struct definition, and validator function for this specific field group. This code can be exported into any external project to be used in addition to the CLI tool.

3. Run `make install`.

This will bundle up our newly created field group files into an executable that can be ran from the command line.

4. Run `config-tool validate -c <path-to-config>`

If we run our newly created validation tool against the following `config.yaml`, we should get an error since `SECURITY_SCANNER_ENDPOINT` must be present if `FEATURE_SECURITY_SCANNER` is on.

`config.yaml`

```
FEATURE_SECURITY_SCANNER: true
FEATURE_SECURITY_NOTIFICATIONS: false
```

This config returns the following:

```
+-----------------+-------------------------+--------------------------------------+--------+
|   FIELD GROUP   |          FIELD          |             ERROR                    | STATUS |
+-----------------+-------------------------+--------------------------------------+--------+
| SecurityScanner | SecurityScannerEndpoint | Field enforces tag:                  | 🔴     |
|                 |                         | required_with FeatureSecurityScanner |        |
+-----------------+-------------------------+--------------------------------------+--------+
```

If we fix our `config.yaml` to the following:

```
FEATURE_SECURITY_SCANNER: true
FEATURE_SECURITY_NOTIFICATIONS: false
SECURITY_SCANNER_ENDPOINT: localhost:8080
```

This config returns the following:

```
+-----------------+-------+-------+--------+
|   FIELD GROUP   | FIELD | ERROR | STATUS |
+-----------------+-------+-------+--------+
| SecurityScanner | -     | -     | 🟢     |
+-----------------+-------+-------+--------+
```
