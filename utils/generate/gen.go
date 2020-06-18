package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"path"
	"runtime"
	"strings"

	"github.com/dave/jennifer/jen"
)

// ConfigDefinition holds the information about different
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

//go:generate go run gen.go
func main() {

	// Read config definition file
	configDefFile, err := ioutil.ReadFile("fieldgroups.json")
	if err != nil {
		fmt.Println(err.Error())
	}

	// Load config definition file into struct
	var configDef ConfigDefinition
	if err = json.Unmarshal(configDefFile, &configDef); err != nil {
		fmt.Println("error: " + err.Error())
	}

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

		// Struct Definition
		f.Comment(fgName + "FieldGroup represents the " + fgName + " config fields")
		structBlock := generateStructBlock(fields)
		f.Type().Id(fgName + "FieldGroup").Struct(structBlock)

		// Constructor
		f.Comment("New" + fgName + "FieldGroup creates a new " + fgName + "FieldGroup")
		constructor := generateConstructor(fgName, fields)
		f.Add(constructor)

		// Create Validator function
		f.Comment("Validate checks the configuration settings for this field group")
		f.Func().Params(jen.Id("fg *"+fgName+"FieldGroup")).Id("Validate").Params().Params(jen.Qual("github.com/go-playground/validator/v10", "ValidationErrors")).Block(
			jen.Id("validate").Op(":=").Qual("github.com/go-playground/validator/v10", "New").Call(),
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

	// Define outputfile name
	outfile := "config.go"
	outfilePath := getFullOutputPath(outfile)
	if err := f.Save(outfilePath); err != nil {
		return err
	}

	return nil

}

/*************************************************
            Generate Block Contents
*************************************************/

// generateStructDefaults generates a struct definition block
func generateStructBlock(fields []FieldDefinition) *jen.Statement {

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
			case "[]interface{}":
				g.Id(fieldName).Index().Interface().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "bool":
				g.Id(fieldName).Bool().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "string":
				g.Id(fieldName).String().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "int":
				g.Id(fieldName).Int().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			case "interface{}":
				g.Id(fieldName).Struct(generateStructBlock(field.Properties)).Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
			default:

			}

		}
	})

	return structBlock

}

// generateConstructorBlock generates a constructor block
func generateConstructor(fgName string, fields []FieldDefinition) *jen.Statement {

	// Create default values dynamically
	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	setValues := jen.CustomFunc(op, func(g *jen.Group) {

		for _, field := range fields {

			g.If(jen.List(jen.Id("value"), jen.Id("ok")).Op(":=").Id("fullConfig").Index(jen.Lit(field.YAML)), jen.Id("ok")).Block(
				jen.Id("new" + fgName).Dot(field.Name).Op("=").Id("value").Assert(jen.Id(field.Type)),
			)

		}
	})

	constructor := jen.Func().Id("New"+fgName+"FieldGroup").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id("FieldGroup").Block(
		jen.Id("new"+fgName).Op(":=").Op("&").Id(fgName+"FieldGroup").Values(),
		jen.Qual("github.com/creasty/defaults", "Set").Call(jen.Id("new"+fgName)),
		setValues,
		jen.Return(jen.Id("new"+fgName)),
	)

	return constructor

}

/************************************************
              Helper Functions
************************************************/

// getFullOutputPath returns the full path to an output file
func getFullOutputPath(fileName string) string {
	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", "fieldgroups"))
	fullPath := path.Join(projRoot, fileName)
	return fullPath
}
