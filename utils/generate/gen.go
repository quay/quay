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

// FieldGroupDefinition is a struct that represents a fieldgroup definition
type FieldGroupDefinition struct {
	PackageName string       `json:"packageName"`
	FieldGroups []FieldGroup `json:"fieldGroups"`
}

// FieldGroup is a struct that represents a single field group
type FieldGroup struct {
	FieldGroupName string  `json:"fieldGroupName"`
	Fields         []Field `json:"fields"`
}

// Field is a struct that represents a single field
type Field struct {
	Name       string  `json:"name"`
	YAML       string  `json:"yaml"`
	Type       string  `json:"type"`
	Default    string  `json:"default"`
	Validate   string  `json:"validate"`
	Properties []Field `json:"properties"`
}

//go:generate go run gen.go
func main() {

	// Read config file
	fieldGroupDefinitionFile, err := ioutil.ReadFile("fieldgroups.json")
	if err != nil {
		return
	}

	// Load field group definitions
	var fgd FieldGroupDefinition
	if err = json.Unmarshal(fieldGroupDefinitionFile, &fgd); err != nil {
		fmt.Println("error: " + err.Error())
	}

	// Create base config file
	err = createConfigBase(fgd)
	if err != nil {
		return
	}

	// Create field group files
	err = createFieldGroups(fgd)
	if err != nil {
		return
	}

}

func createFieldGroups(fgd FieldGroupDefinition) error {
	// For each field group, create structs, constructors, and validate function
	for _, fieldGroup := range fgd.FieldGroups {

		// Create package name
		packageName := fgd.PackageName
		f := jen.NewFile(packageName)
		f.ImportName("github.com/creasty/defaults", "defaults")
		f.ImportName("github.com/go-playground/validator/v10", "validator")

		// Generate attributes
		attributes := generateStructAttributes(fieldGroup.Fields)

		// Create struct definition
		f.Comment(fieldGroup.FieldGroupName + "FieldGroup represents the " + fieldGroup.FieldGroupName + " config fields")
		f.Type().Id(fieldGroup.FieldGroupName + "FieldGroup").Struct(attributes)

		defaultValues := generateStructDefaults(fieldGroup)

		// Create constructor
		f.Comment("New" + fieldGroup.FieldGroupName + "FieldGroup creates a new " + fieldGroup.FieldGroupName + "FieldGroup")
		f.Func().Id("New"+fieldGroup.FieldGroupName+"FieldGroup").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id("FieldGroup").Block(
			jen.Id("new"+fieldGroup.FieldGroupName).Op(":=").Op("&").Id(fieldGroup.FieldGroupName+"FieldGroup").Values(),
			jen.Qual("github.com/creasty/defaults", "Set").Call(jen.Id("new"+fieldGroup.FieldGroupName)),
			defaultValues,
			jen.Return(jen.Id("new"+fieldGroup.FieldGroupName)),
		)

		// Create Validator function
		f.Comment("Validate checks the configuration settings for this field group")
		f.Func().Params(jen.Id("fg *"+fieldGroup.FieldGroupName+"FieldGroup")).Id("Validate").Params().Params(jen.Qual("github.com/go-playground/validator/v10", "ValidationErrors")).Block(
			jen.Id("validate").Op(":=").Qual("github.com/go-playground/validator/v10", "New").Call(),
			jen.Id("err").Op(":=").Id("validate").Dot("Struct").Call(jen.Id("fg")),
			jen.If(jen.Id("err").Op("==").Nil()).Block(
				jen.Return(jen.Nil()),
			),
			jen.Id("validationErrors").Op(":=").Id("err").Assert(jen.Id("validator").Dot("ValidationErrors")),
			jen.Return(jen.Id("validationErrors")),
		)

		// Define outputfile name
		// Get root of project
		_, b, _, _ := runtime.Caller(0)
		projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", "fieldgroups"))
		outfile := strings.ToLower(fieldGroup.FieldGroupName + ".go")
		outfilePath := path.Join(projRoot, outfile)
		f.Save(outfilePath)

	}
	return nil

}

func generateStructAttributes(fields []Field) *jen.Statement {

	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	attributes := jen.CustomFunc(op, func(g *jen.Group) {

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
			case "object":
				g.Id(fieldName).Struct(generateStructAttributes(field.Properties))
			default:

			}

		}
	})

	return attributes

}

func generateStructDefaults(fieldGroup FieldGroup) *jen.Statement {
	// Create default values dynamically
	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	defaultValues := jen.CustomFunc(op, func(g *jen.Group) {

		for _, field := range fieldGroup.Fields {

			g.If(jen.List(jen.Id("value"), jen.Id("ok")).Op(":=").Id("fullConfig").Index(jen.Lit(field.YAML)), jen.Id("ok")).Block(
				jen.Id("new" + fieldGroup.FieldGroupName).Dot(field.Name).Op("=").Id("value").Assert(jen.Id(field.Type)),
			)

		}
	})

	return defaultValues
}

func createConfigBase(fgd FieldGroupDefinition) error {

	// Create file for QuayConfig
	packageName := fgd.PackageName
	fStruct := jen.NewFile(packageName)
	fStruct.ImportName("github.com/go-playground/validator/v10", "validator")
	fStruct.Comment("FieldGroup is an interface that implements the Validate() function")
	fStruct.Type().Id("FieldGroup").Interface(jen.Id("Validate").Params().Parens(jen.List(jen.Qual("github.com/go-playground/validator/v10", "ValidationErrors"))))

	fStruct.Comment("Config is a struct that represents a configuration as a mapping of field groups")
	fStruct.Type().Id("Config").Map(jen.String()).Id("FieldGroup")
	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	fgConstructors := jen.CustomFunc(op, func(g *jen.Group) {

		g.Id("newConfig").Op(":=").Id("Config").Values()
		for _, fieldGroup := range fgd.FieldGroups {
			g.Id("newConfig").Index(jen.Lit(fieldGroup.FieldGroupName)).Op("=").Id("New" + fieldGroup.FieldGroupName + "FieldGroup").Call(jen.Id("fullConfig"))
		}

	})
	fStruct.Comment("NewConfig creates a Config struct from a map[string]interface{}")
	fStruct.Func().Id("NewConfig").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id("Config").Block(fgConstructors, jen.Return(jen.Id("newConfig")))

	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", "fieldgroups"))
	outfile := "config.go"
	outfilePath := path.Join(projRoot, outfile)
	fStruct.Save(outfilePath)

	return nil
}
