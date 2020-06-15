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
	FieldName    string `json:"fieldName"`
	FieldYAML    string `json:"fieldYAML"`
	FieldType    string `json:"fieldType"`
	FieldDefault string `json:"fieldDefault"`
}

//go:generate go run gen.go
func main() {

	// Get root of project
	_, b, _, _ := runtime.Caller(0)
	projRoot := path.Join(path.Dir(b))
	fmt.Println("Relative", projRoot)

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

	for _, fieldGroup := range fgd.FieldGroups {

		// Create package name
		f := jen.NewFile(packageName)

		op := jen.Options{
			Open:  "\n",
			Multi: true,
			Close: "\n",
		}
		attributes := jen.CustomFunc(op, func(g *jen.Group) {

			for _, field := range fieldGroup.Fields {

				// hacky fix to escape string
				fieldDefault := strings.Replace(field.FieldDefault, `"`, `\"`, -1)

				switch field.FieldType {
				case "array":
					g.Id(field.FieldName).Index().String().Tag(map[string]string{"default": fieldDefault})
				case "boolean":
					g.Id(field.FieldName).Bool().Tag(map[string]string{"default": fieldDefault})
				case "string":
					g.Id(field.FieldName).String().Tag(map[string]string{"default": field.FieldDefault})
				default:

				}

			}
		})

		// Create struct definition
		f.Comment("Struct Definition")
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
					jen.Id("new" + fieldGroup.FieldGroupName).Dot(field.FieldName).Op("=").Id("value"),
				)

			}
		})

		// Create constructor
		f.Comment("Constructor")
		f.Func().Id("New"+fieldGroup.FieldGroupName+"FieldGroup").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id("FieldGoup").Block(
			jen.Id("new"+fieldGroup.FieldGroupName).Op(":=").Op("&").Id(fieldGroup.FieldGroupName+"FieldGroup").Values(),
			jen.Id("defaults").Dot("Set").Call(jen.Id("new"+fieldGroup.FieldGroupName)),
			defaultValues,
			jen.Return(jen.Id("new"+fieldGroup.FieldGroupName)),
		)

		// Create Validator function
		f.Comment("Validator Function")
		f.Func().Params(jen.Id("fg *"+fieldGroup.FieldGroupName+"FieldGroup")).Id("Validate").Params().Params(jen.Bool(), jen.Error()).Block(
			jen.Return(jen.True(), jen.Nil()),
		)

		// Define outputfile name
		outfile := strings.ToLower(fieldGroup.FieldGroupName + ".go")
		outfilePath := path.Join(projRoot, outfile)
		fmt.Println(outfilePath)

	}

}
