package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path"
	"runtime"
	"sort"
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
	FieldGroups []string                  `json:"ct-fieldgroups"`
	Properties  map[string]SchemaProperty `json:"properties"`
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
		f := jen.NewFile(strings.ToLower(fgName))

		// Import statements based on presence
		f.ImportName("github.com/creasty/defaults", "defaults")
		f.ImportName("github.com/go-playground/validator/v10", "validator")
		f.ImportName("github.com/quay/config-tool/pkg/lib/shared", "shared")

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

		// Create Validator file
		v := jen.NewFile(strings.ToLower(fgName))
		v.ImportName("github.com/quay/config-tool/pkg/lib/shared", "shared")
		v.Comment("Validate checks the configuration settings for this field group")
		v.Func().Params(jen.Id("fg *" + fgName + "FieldGroup")).Id("Validate").Params().Params(jen.Index().Qual("github.com/quay/config-tool/pkg/lib/shared", "ValidationError")).Block(
			jen.Return(jen.Nil()),
		)

		// Create test file
		t := jen.NewFile(strings.ToLower(fgName))
		t.ImportName("testing", "testing")
		t.Comment("TestValidate" + fgName + " tests the Validate function")
		t.Func().Id("TestValidate"+fgName).Params(jen.Id("t").Qual("testing", "T")).Block(
			jen.Var().Id("tests").Op("=").Index().Struct(
				jen.Id("name").String(),
				jen.Id("config").Map(jen.String()).Interface(),
				jen.Id("want").String(),
			).Values(jen.Values(jen.Dict{
				jen.Id("name"):   jen.Lit("testOne"),
				jen.Id("config"): jen.Map(jen.String()).Interface().Values(jen.Dict{}),
				jen.Id("want"):   jen.Lit("valid"),
			})),
			jen.For().List(jen.Id("_"), jen.Id("tt")).Op(":=").Range().Id("tests").Block(
				jen.Qual("fmt", "Println").Call(jen.Lit("hello")),
			),
		)

		// Output files if package does not already exist
		packagePath := getFullPackageOutputPath(strings.ToLower(fgName))
		if _, err := os.Stat(packagePath); os.IsNotExist(err) {

			// create directory
			os.Mkdir(packagePath, 0777)

			// Generate file path
			dOutfile := getFullFileOutputPath(strings.ToLower(fgName), strings.ToLower(fgName)+".go")
			fmt.Println(dOutfile)
			f.Save(dOutfile)

			vOutfile := getFullFileOutputPath(strings.ToLower(fgName), strings.ToLower(fgName)+"_validator.go")
			if err := v.Save(vOutfile); err != nil {
				fmt.Println(err.Error())
			}

			tOutfile := getFullFileOutputPath(strings.ToLower(fgName), strings.ToLower(fgName)+"_test.go")
			if err := t.Save(tOutfile); err != nil {
				fmt.Println(err.Error())
			}

		}

		// Implement fields function
		fFile := jen.NewFile(strings.ToLower(fgName))
		fFile.Comment("Fields returns a list of strings representing the fields in this field group")
		fFile.Func().Params(jen.Id("fg *" + fgName + "FieldGroup")).Id("Fields").Params().Params(jen.Index().String()).Block(
			jen.Return(jen.Index().String().ValuesFunc(func(g *jen.Group) {
				for _, field := range fields {
					g.Lit(field.YAML)
				}
			}),
			),
		)
		fOutfile := getFullFileOutputPath(strings.ToLower(fgName), strings.ToLower(fgName)+"_fields.go")
		if err := fFile.Save(fOutfile); err != nil {
			fmt.Println(err.Error())
		}

	}
	return nil

}

// createConfigBase will create the base configuration file in the fieldgroups package
func createConfigBase(configDef ConfigDefinition) error {

	// Create file for QuayConfig
	f := jen.NewFile("config")
	f.ImportName("github.com/quay/config-tool/pkg/lib/shared", "shared")

	// Write Config struct definition
	f.Comment("Config is a struct that represents a configuration as a mapping of field groups")
	f.Type().Id("Config").Map(jen.String()).Qual("github.com/quay/config-tool/pkg/lib/shared", "FieldGroup")

	// Generate Config constructor block
	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	constructorBlock := jen.CustomFunc(op, func(g *jen.Group) {
		g.Var().Id("err").Error()
		g.Id("newConfig").Op(":=").Id("Config").Values()
		for fgName := range configDef {
			g.List(jen.Id("new"+fgName+"FieldGroup"), jen.Id("err")).Op(":=").Id(strings.ToLower(fgName) + ".New" + fgName + "FieldGroup").Call(jen.Id("fullConfig"))
			g.If(jen.Id("err").Op("!=").Nil()).Block(
				jen.Return(jen.List(jen.Id("newConfig"), jen.Id("err"))),
			)
			g.Id("newConfig").Index(jen.Lit(fgName)).Op("=").Id("new" + fgName + "FieldGroup")
		}

	})

	// Write Config constructor
	f.Comment("NewConfig creates a Config struct from a map[string]interface{}")
	f.Func().Id("NewConfig").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Parens(jen.List(jen.Id("Config"), jen.Error())).Block(constructorBlock, jen.Return(jen.List(jen.Id("newConfig"), jen.Nil())))

	// Define outputfile name
	outfile := "config.go"
	outfilePath := getFullConfigOutputPath("config", outfile)
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
			fieldYAML := field.YAML

			switch field.Type {
			case "array":
				g.Id(fieldName).Index().Interface().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate, "yaml": fieldYAML})
			case "boolean":
				g.Id(fieldName).Bool().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate, "yaml": fieldYAML})
			case "string":
				g.Id(fieldName).String().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate, "yaml": fieldYAML})
			case "number":
				g.Id(fieldName).Int().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate, "yaml": fieldYAML})
			case "object":
				g.Id(fieldName).Id("*" + fieldName + "Struct").Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate, "yaml": fieldYAML})
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
		returnType = "*" + fgName

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
					jen.Var().Id("err").Error(),
					jen.Id("value").Op(":=").Id("shared.FixInterface").Call(jen.Id("value").Assert(jen.Map(jen.Interface()).Interface())),
					jen.List(jen.Id("new"+fgName).Dot(field.Name), jen.Id("err")).Op("=").Id("New"+field.Name+"Struct").Call(jen.Id("value")),
					jen.If(jen.Id("err").Op("!=").Nil()).Block(jen.Return(jen.List(jen.Id("new"+fgName), jen.Id("err")))),
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
					jen.List(jen.Id("new"+fgName).Dot(field.Name), jen.Id("ok")).Op("=").Id("value").Assert(jen.Id(ftype)),
					jen.If(jen.Id("!ok")).Block(jen.Return(jen.List(jen.Id("new"+fgName), jen.Qual("errors", "New").Call(jen.Lit(field.YAML+" must be of type "+ftype))))),
				)
			}

		}

	})

	constructor := jen.Comment("// New" + fgName + " creates a new " + fgName + "\n")

	// If the field is just a map[string]interface{}
	if len(fields) == 0 {
		constructor.Add(jen.Func().Id("New"+fgName).Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Parens(jen.List(jen.Id(returnType), jen.Error())).Block(
			jen.Id("new"+fgName).Op(":=").Id(fgName).Values(),
			jen.For(jen.List(jen.Id("key"), jen.Id("value")).Op(":=").Range().Id("fullConfig").Block(
				jen.Id("new"+fgName).Index(jen.Id("key")).Op("=").Id("value"),
			)),
			jen.Return(jen.List(jen.Id("&new"+fgName), jen.Nil())),
		))
	} else {
		constructor.Add(jen.Func().Id("New"+fgName).Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Parens(jen.List(jen.Id(returnType), jen.Error())).Block(
			jen.Id("new"+fgName).Op(":=").Op("&").Id(fgName).Values(),
			jen.Qual("github.com/creasty/defaults", "Set").Call(jen.Id("new"+fgName)),
			setValues,
			jen.Return(jen.List(jen.Id("new"+fgName), jen.Nil())),
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

	// Sort keys to enforce consistent order
	var fieldNames []string
	for fieldName := range properties {
		fieldNames = append(fieldNames, fieldName)
	}
	sort.Strings(fieldNames)

	// Iterate through keys and get data from properties
	for _, fieldName := range fieldNames {

		// Get field data for this field
		fieldData := properties[fieldName]

		// Convert to correct format
		fieldDef := propertySchemaToFieldDefinition(fieldName, fieldData)

		// Iterate through different field groups for this specific field
		for _, fgName := range fieldData.FieldGroups {

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
func getFullPackageOutputPath(packageName string) string {
	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", "fieldgroups"))
	fullPath := path.Join(projRoot, packageName)
	return fullPath
}

func getFullFileOutputPath(packageName, fileName string) string {
	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", "fieldgroups", packageName))
	fullPath := path.Join(projRoot, fileName)
	return fullPath
}

func getFullConfigOutputPath(packageName, fileName string) string {
	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", packageName))
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

// dumpStruct will pretty print a struct
func dumpStruct(i interface{}) string {
	spew.Config.Indent = "\t"
	spew.Config.DisableCapacities = true
	spew.Config.DisablePointerAddresses = true
	spew.Config.SortKeys = true
	spew.Config.DisableMethods = true
	spew.Config.DisableTypes = true
	spew.Config.DisableLengths = true
	return spew.Sdump(i)
}
