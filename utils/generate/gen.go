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
	FieldName     string `json:"fieldName"`
	FieldYAML     string `json:"fieldYAML"`
	FieldType     string `json:"fieldType"`
	FieldDefault  string `json:"fieldDefault"`
	FieldValidate string `json:"fieldValidate"`
}

//go:generate go run gen.go
func main() {

	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(path.Dir(path.Dir(b))), path.Join("pkg", "lib", "fieldgroups"))

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

	// Get package name
	packageName := fgd.PackageName

	// Create file for QuayConfig
	fStruct := jen.NewFile(packageName)
	fStruct.ImportName("github.com/go-playground/validator/v10", "validator")
	fStruct.Comment("FieldGroup is an interface that implements the Validate() function")
	fStruct.Type().Id("FieldGroup").Interface(jen.Id("Validate").Params().Parens(jen.List(jen.Qual("github.com/go-playground/validator/v10", "ValidationErrors"))))

	fStruct.Comment("Config is a struct that represents a configuration as a mapping of field groups")
	fStruct.Type().Id("Config").Map(jen.String()).Id("FieldGroup")

	// Call constructor

	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}

	fgConstructors := jen.CustomFunc(op, func(g *jen.Group) {

		g.Id("newConfig").Op(":=").Op("&").Id("Config").Values()
		for _, fieldGroup := range fgd.FieldGroups {
			g.Id("newConfig").Index(jen.Lit(fieldGroup.FieldGroupName)).Op("=").Id("New" + fieldGroup.FieldGroupName).Call(jen.Id("fullConfig"))
		}

	})

	fStruct.Comment("NewConfig creates a Config struct from a map[string]interface{}")
	fStruct.Func().Id("NewConfig").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id("*Config").Block(fgConstructors, jen.Return(jen.Id("newConfig")))

	outfile := "quayconfig.go"
	outfilePath := path.Join(projRoot, outfile)
	fStruct.Save(outfilePath)

	// For each field group, create structs, constructors, and validate function
	for _, fieldGroup := range fgd.FieldGroups {

		// Create package name
		f := jen.NewFile(packageName)
		f.ImportName("github.com/creasty/defaults", "defaults")
		f.ImportName("github.com/go-playground/validator/v10", "validator")

		op = jen.Options{
			Open:  "\n",
			Multi: true,
			Close: "\n",
		}
		attributes := jen.CustomFunc(op, func(g *jen.Group) {

			for _, field := range fieldGroup.Fields {

				// hacky fix to escape string
				fieldDefault := strings.Replace(field.FieldDefault, `"`, `\"`, -1)
				fieldValidate := field.FieldValidate

				switch field.FieldType {
				case "[]string":
					g.Id(field.FieldName).Index().String().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
				case "bool":
					g.Id(field.FieldName).Bool().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
				case "string":
					g.Id(field.FieldName).String().Tag(map[string]string{"default": fieldDefault, "validate": fieldValidate})
				default:

				}

			}
		})

		// Create struct definition
		f.Comment(fieldGroup.FieldGroupName + "FieldGroup represents the " + fieldGroup.FieldGroupName + " config fields")
		f.Type().Id(fieldGroup.FieldGroupName + "FieldGroup").Struct(attributes)

		// Create default values dynamically
		op = jen.Options{
			Open:  "\n",
			Multi: true,
			Close: "\n",
		}
		defaultValues := jen.CustomFunc(op, func(g *jen.Group) {

			for _, field := range fieldGroup.Fields {

				g.If(jen.List(jen.Id("value"), jen.Id("ok")).Op(":=").Id("fullConfig").Index(jen.Lit(field.FieldYAML)), jen.Id("ok")).Block(
					jen.Id("new" + fieldGroup.FieldGroupName).Dot(field.FieldName).Op("=").Id("value").Assert(jen.Id(field.FieldType)),
				)

			}
		})

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
		f.Func().Params(jen.Id("fg *"+fieldGroup.FieldGroupName+"FieldGroup")).Id("Validate").Params().Params(jen.Qual("github.com/go-playground/validator/v10", "ValidationErrors"), jen.Error()).Block(
			jen.Id("validate").Op(":=").Qual("github.com/go-playground/validator/v10", "New").Call(),
			jen.Id("err").Op(":=").Id("validate").Dot("Struct").Call(jen.Id("fg")),
			jen.Id("validationErrors").Op(":=").Id("err").Assert(jen.Id("validator").Dot("ValidationErrors")),
			jen.Return(jen.Id("validationErrors")),
		)

		// Define outputfile name
		outfile = strings.ToLower(fieldGroup.FieldGroupName + ".go")
		outfilePath = path.Join(projRoot, outfile)
		f.Save(outfilePath)

	}

}
