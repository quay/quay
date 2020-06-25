package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"path"
	"runtime"
	"strings"

	"github.com/dave/jennifer/jen"
	"github.com/iancoleman/strcase"
	"github.com/jojomi/go-spew/spew"
)

// ConfigDefinition holds the information about different field groups
type ConfigDefinition map[string][]FieldDefinition

// FieldDefinition is a struct that represents a single field from a fieldgroups.json file
type FieldDefinition struct {
	Name       string            `json:"name"`
	YAML       string            `json:"yaml"`
	Type       string            `json:"type"`
	Default    string            `json:"default"`
	Validate   string            `json:"validate"`
	Properties []FieldDefinition `json:"properties"`
}

// JSONSchema is a type used to represent a Json Schema file
type JSONSchema struct {
	Type        string                    `json:"object"`
	Description string                    `json:"description"`
	Properties  map[string]SchemaProperty `json:"properties"`
}

// SchemaProperty is a type that holds field data from a json schema file. This is how a field is represented before it is converted to a FieldDefinition.
type SchemaProperty struct {
	Type        string `json:"type"`
	Description string `json:"description"`
	Default     string `json:"ct-default"`
	Validate    string `json:"ct-validate"`
	Items       []struct {
		Type string `json:"type"`
	} `json:"items"`
	FieldGroupData map[string]map[string]interface{} `json:"ct-fieldgroups"`
	Properties     map[string]SchemaProperty         `json:"properties"`
}

//go:generate go run gen.go
func main() {

	// Read config definition file
	jsonSchemaPath := getFullInputPath("schema.json")
	jsonSchemaFile, err := ioutil.ReadFile(jsonSchemaPath)
	if err != nil {
		fmt.Println(err.Error())
	}

	// Load config definition file into struct
	var jsonSchema JSONSchema
	if err = json.Unmarshal(jsonSchemaFile, &jsonSchema); err != nil {
		fmt.Println("error: " + err.Error())
	}

	// Convert JSON Schema to Config Definiton
	configDef := jsonSchemaPropertiesToConfigDefinition(jsonSchema)

	spew.Config.Indent = "\t"
	spew.Config.DisableCapacities = true
	spew.Config.DisablePointerAddresses = true
	spew.Config.SortKeys = true
	spew.Config.DisableMethods = true
	spew.Config.DisableTypes = true
	spew.Config.DisableLengths = true
	spew.Dump(configDef)

	// Create config.go
	err = createConfigBase(configDef)
	if err != nil {
		fmt.Println(err.Error())
	}

	// Create field group files
	err = createFieldGroups(configDef)
	if err != nil {
		fmt.Println(err.Error())
	}

}

/**************************************************
                Generate Files
**************************************************/

// createFieldGroups will generate a .go file for a field group defined struct
func createFieldGroups(configDef ConfigDefinition) error {

	// For each field group, create structs, constructors, and validate function
	for fgName, fields := range configDef {

		// Create file for field group
		f := jen.NewFile("fieldgroups")

		// Import statements based on presence
		f.ImportName("github.com/creasty/defaults", "defaults")
		f.ImportName("github.com/go-playground/validator/v10", "validator")

		// Struct Definitions
		structsList := reverseList(generateStructs(fgName, fields, true))
		op := jen.Options{
			Open:  "\n",
			Multi: true,
			Close: "\n",
		}
		f.CustomFunc(op, func(g *jen.Group) {
			for _, structDef := range structsList {
				g.Add(structDef)
			}
		})

		// Constructor Definitions
		constructorsList := reverseList(generateConstructors(fgName, fields, true))
		op = jen.Options{
			Open:  "\n",
			Multi: true,
			Close: "\n",
		}
		f.CustomFunc(op, func(g *jen.Group) {
			for _, constructorDef := range constructorsList {
				g.Add(constructorDef)
			}
		})

		// Find custom validators in field group and register
		customValidators := findCustomValidator(fields)
		registerValidators := jen.Empty()
		op = jen.Options{
			Open:  "\n",
			Multi: true,
			Close: "\n",
		}
		registerValidators.CustomFunc(op, func(g *jen.Group) {
			for _, customValidator := range customValidators {
				g.Add(jen.Id("validate").Dot("RegisterValidation").Call(jen.List(jen.Lit(customValidator), jen.Id(customValidator))))
			}
		})

		// Create Validator function
		f.Comment("Validate checks the configuration settings for this field group")
		f.Func().Params(jen.Id("fg *"+fgName+"FieldGroup")).Id("Validate").Params().Params(jen.Qual("github.com/go-playground/validator/v10", "ValidationErrors")).Block(
			jen.Id("validate").Op(":=").Qual("github.com/go-playground/validator/v10", "New").Call(),
			registerValidators,
			jen.Id("err").Op(":=").Id("validate").Dot("Struct").Call(jen.Id("fg")),
			jen.If(jen.Id("err").Op("==").Nil()).Block(
				jen.Return(jen.Nil()),
			),
			jen.Id("validationErrors").Op(":=").Id("err").Assert(jen.Id("validator").Dot("ValidationErrors")),
			jen.Return(jen.Id("validationErrors")),
		)

		// Define outputfile name
		outfile := strings.ToLower(fgName + ".go")
		outfilePath := getFullOutputPath(outfile)
		if err := f.Save(outfilePath); err != nil {
			return err
		}

	}
	return nil

}

// createConfigBase will create the base configuration file in the fieldgroups package
func createConfigBase(configDef ConfigDefinition) error {

	// Create file for QuayConfig
	f := jen.NewFile("fieldgroups")

	// Import packages
	f.ImportName("github.com/go-playground/validator/v10", "validator")

	// Write FieldGroup interface
	f.Comment("FieldGroup is an interface that implements the Validate() function")
	f.Type().Id("FieldGroup").Interface(jen.Id("Validate").Params().Parens(jen.List(jen.Qual("github.com/go-playground/validator/v10", "ValidationErrors"))))

	// Write Config struct definition
	f.Comment("Config is a struct that represents a configuration as a mapping of field groups")
	f.Type().Id("Config").Map(jen.String()).Id("FieldGroup")

	// Generate Config constructor block
	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	constructorBlock := jen.CustomFunc(op, func(g *jen.Group) {

		g.Id("newConfig").Op(":=").Id("Config").Values()
		for fgName := range configDef {
			g.Id("newConfig").Index(jen.Lit(fgName)).Op("=").Id("New" + fgName + "FieldGroup").Call(jen.Id("fullConfig"))
		}

	})

	// Write Config constructor
	f.Comment("NewConfig creates a Config struct from a map[string]interface{}")
	f.Func().Id("NewConfig").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id("Config").Block(constructorBlock, jen.Return(jen.Id("newConfig")))

	// Add helper function to fix maps
	f.Comment("fixInterface converts a map[interface{}]interface{} into a map[string]interface{}")
	f.Func().Id("fixInterface").Params(jen.Id("input").Map(jen.Interface()).Interface()).Map(jen.String()).Interface().Block(
		jen.Id("output").Op(":=").Make(jen.Map(jen.String()).Interface()),
		jen.For(jen.List(jen.Id("key"), jen.Id("value")).Op(":=").Range().Id("input").Block(
			jen.Id("strKey").Op(":=").Qual("fmt", "Sprintf").Call(jen.List(jen.Lit("%v"), jen.Id("key"))),
			jen.Id("output").Index(jen.Id("strKey")).Op("=").Id("value"),
		)),
		jen.Return(jen.Id("output")),
	)

	// Define outputfile name
	outfile := "config.go"
	outfilePath := getFullOutputPath(outfile)
	if err := f.Save(outfilePath); err != nil {
		return err
	}

	return nil

}

/*************************************************
                Generate Blocks
*************************************************/

// generateStructDefaults generates a struct definition block
func generateStructs(fgName string, fields []FieldDefinition, topLevel bool) (structs []*jen.Statement) {

	var innerStructs []*jen.Statement = []*jen.Statement{}

	// If top level is true, this struct is a field group
	if topLevel {
		fgName = fgName + "FieldGroup"

	} else { // Otherwise it is a inner struct
		fgName = fgName + "Struct"
	}

	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	structBlock := jen.CustomFunc(op, func(g *jen.Group) {

		for _, field := range fields {

			// hacky fix to escape string
			fieldName := field.Name
			fieldDefault := strings.Replace(field.Default, `"`, `\"`, -1)
			fieldValidate := field.Validate

			switch field.Type {
			case "array":
				g.Id(fieldName).Index().Interface().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "boolean":
				g.Id(fieldName).Bool().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "string":
				g.Id(fieldName).String().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "number":
				g.Id(fieldName).Int().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "object":
				g.Id(fieldName).Id("*" + fieldName + "Struct").Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
				if len(field.Properties) == 0 {
					innerStructs = append(innerStructs, jen.Comment("// "+fieldName+"Struct represents the "+fieldName+" struct\n").Type().Id(fieldName+"Struct").Map(jen.String()).Interface())
				} else {
					innerStructs = append(innerStructs, generateStructs(fieldName, field.Properties, false)...)
				}
			default:

			}

		}
	})

	structDef := jen.Comment("// " + fgName + " represents the " + fgName + " config fields\n")
	structDef.Add(jen.Type().Id(fgName).Struct(structBlock))

	return append(innerStructs, structDef)

}

// generateConstructorBlock generates a constructor block
func generateConstructors(fgName string, fields []FieldDefinition, topLevel bool) (constructors []*jen.Statement) {

	var innerConstructors []*jen.Statement = []*jen.Statement{}
	var returnType string

	// If top level is true, this struct is a field group
	if topLevel {
		fgName = fgName + "FieldGroup"
		returnType = "FieldGroup"

	} else { // Otherwise it is a inner struct
		fgName = fgName + "Struct"
		returnType = "*" + fgName
	}

	// Load values from map[string]interface{}
	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	setValues := jen.CustomFunc(op, func(g *jen.Group) {

		for _, field := range fields {

			// If the field is a nested struct
			if field.Type == "object" {
				g.If(jen.List(jen.Id("value"), jen.Id("ok")).Op(":=").Id("fullConfig").Index(jen.Lit(field.YAML)), jen.Id("ok")).Block(
					jen.Id("value").Op(":=").Id("fixInterface").Call(jen.Id("value").Assert(jen.Map(jen.Interface()).Interface())),
					jen.Id("new"+fgName).Dot(field.Name).Op("=").Id("New"+field.Name+"Struct").Call(jen.Id("value")),
				)

				innerConstructors = append(innerConstructors, generateConstructors(field.Name, field.Properties, false)...)

			} else { // If the field is a primitive

				// Translate type to go type
				var ftype string
				switch field.Type {
				case "array":
					ftype = "[]interface{}"
				case "boolean":
					ftype = "bool"
				case "string":
					ftype = "string"
				case "number":
					ftype = "int"
				default:
				}

				g.If(jen.List(jen.Id("value"), jen.Id("ok")).Op(":=").Id("fullConfig").Index(jen.Lit(field.YAML)), jen.Id("ok")).Block(
					jen.Id("new" + fgName).Dot(field.Name).Op("=").Id("value").Assert(jen.Id(ftype)),
				)
			}

		}

	})

	constructor := jen.Comment("// New" + fgName + " creates a new " + fgName + "\n")

	// If the field is just a map[string]interface{}
	if len(fields) == 0 {
		constructor.Add(jen.Func().Id("New"+fgName).Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id(returnType).Block(
			jen.Id("new"+fgName).Op(":=").Id(fgName).Values(),
			jen.For(jen.List(jen.Id("key"), jen.Id("value")).Op(":=").Range().Id("fullConfig").Block(
				jen.Id("new"+fgName).Index(jen.Id("key")).Op("=").Id("value"),
			)),
			jen.Return(jen.Id("&new"+fgName)),
		))
	} else {
		constructor.Add(jen.Func().Id("New"+fgName).Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id(returnType).Block(
			jen.Id("new"+fgName).Op(":=").Op("&").Id(fgName).Values(),
			jen.Qual("github.com/creasty/defaults", "Set").Call(jen.Id("new"+fgName)),
			setValues,
			jen.Return(jen.Id("new"+fgName)),
		))
	}

	return append(innerConstructors, constructor)

}

/**************************************************
                Convert Format
**************************************************/

// jsonSchemaToConfigDefinition converts a JSON schema file to the config definition format
func jsonSchemaPropertiesToConfigDefinition(jsonSchema JSONSchema) ConfigDefinition {

	// Create output struct
	configDef := ConfigDefinition{}

	// Get properties
	properties := jsonSchema.Properties

	// Iterate through fields and add to field groups
	for fieldName, fieldData := range properties {

		// Convert to correct format
		fieldDef := propertySchemaToFieldDefinition(fieldName, fieldData)

		// Iterate through different field groups for this specific field
		for fgName, fgSpecificData := range fieldData.FieldGroupData {

			fieldDef := addFieldGroupSpecificData(fieldDef, fgSpecificData)

			// If field group exists, append field definition
			if fg, ok := configDef[fgName]; ok {
				fg := append(fg, fieldDef)
				configDef[fgName] = fg
			} else { // Otherwise create list
				configDef[fgName] = []FieldDefinition{fieldDef}
			}

		}

	}

	// Return config definition
	return configDef
}

// propertySchemaToFieldDefinition will turn a single property schema into a field definition
func propertySchemaToFieldDefinition(fieldName string, fieldData SchemaProperty) FieldDefinition {

	// Get generic information
	name := strcase.ToCamel(strings.ToLower(fieldName))
	yaml := fieldName
	ftype := fieldData.Type
	fdefault := fieldData.Default
	fvalidate := fieldData.Validate
	nestedProperties := []FieldDefinition{}

	// Get nested properties
	for nestedPropName, nestedPropData := range fieldData.Properties {
		nestedProperties = append(nestedProperties, propertySchemaToFieldDefinition(nestedPropName, nestedPropData))
	}

	// Create field definition for with generic information
	fieldDef := FieldDefinition{
		Name:       name,
		YAML:       yaml,
		Type:       ftype,
		Default:    fdefault,
		Validate:   fvalidate,
		Properties: nestedProperties,
	}

	spew.Dump(fieldDef)

	return fieldDef
}

// addFieldGroupSpecificData will append field group specific data to the Field Definition
func addFieldGroupSpecificData(fieldDef FieldDefinition, fgSpecificData map[string]interface{}) FieldDefinition {

	// Check to see if append value exists
	if value, ok := fgSpecificData["ct-validate"]; ok {

		// Check to determine necessity of comma
		if len(fieldDef.Validate) == 0 {
			fieldDef.Validate = value.(string)
		} else {
			fieldDef.Validate = strings.Join([]string{fieldDef.Validate, value.(string)}, ",")
		}

	}

	return fieldDef
}

/************************************************
               Helper Functions
************************************************/

// getFullOutputPath returns the full path to the input file
func getFullInputPath(fileName string) string {
	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("utils", "generate"))
	fullPath := path.Join(projRoot, fileName)
	return fullPath
}

// getFullOutputPath returns the full path to an output file
func getFullOutputPath(fileName string) string {
	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", "fieldgroups"))
	fullPath := path.Join(projRoot, fileName)
	return fullPath
}

// reverseStructOrder reverses the list of structs. TAKEN FROM https://stackoverflow.com/questions/28058278/how-do-i-reverse-a-slice-in-go
func reverseList(structs []*jen.Statement) []*jen.Statement {
	for i, j := 0, len(structs)-1; i < j; i, j = i+1, j-1 {
		structs[i], structs[j] = structs[j], structs[i]
	}

	return structs
}

// findCustomValidator find and register a custom validator
func findCustomValidator(fields []FieldDefinition) []string {

	// Create list of custom validators
	var customValidators []string

	// Iterate through fields
	for _, field := range fields {
		validatorTags := strings.Split(field.Validate, ",")

		// Iterate through individual validator function
		for _, tag := range validatorTags {

			// If tag has custom prefix it is a custom validator
			if strings.HasPrefix(tag, "custom") {
				customValidators = append(customValidators, tag)
			}
		}
	}

	return customValidators
}
