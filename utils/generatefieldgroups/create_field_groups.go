package main

import (
	"fmt"

	"github.com/dave/jennifer/jen"
)

type inputData struct {
	PackageName    string
	FieldGroupName string
	Fields         map[string]fieldData
}

type fieldData struct {
	fieldYAML    string
	fieldType    string
	fieldDefault string
}

func main() {

	data := inputData{
		PackageName:    "fieldgroups",
		FieldGroupName: "TagExpiration",
		Fields: map[string]fieldData{
			"FeatureChangeTagExpiration": {
				fieldYAML:    "FEATURE_CHANGE_TAG_EXPIRATION",
				fieldType:    "bool",
				fieldDefault: "false",
			},
			"DefaultTagExpiration": {
				fieldYAML:    "DEFAULT_TAG_EXPIRATION",
				fieldType:    "string",
				fieldDefault: "2w",
			},
			"TagExpirationOptions": {
				fieldYAML:    "TAG_EXPIRATION_OPTIONS",
				fieldType:    "array",
				fieldDefault: "['0s', '1d', '1w', '2w', '4w']",
			},
		},
	}

	// Create package name
	f := jen.NewFile(data.PackageName)

	op := jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	attributes := jen.CustomFunc(op, func(g *jen.Group) {

		for key, val := range data.Fields {

			switch val.fieldType {
			case "array":
				g.Id(key).Index().String()
			case "bool":
				g.Id(key).Bool()
			case "string":
				g.Id(key).String()
			default:

			}

		}
	})

	// Create struct definition
	f.Comment("Struct Definition")
	f.Type().Id(data.FieldGroupName + "FieldGroup").Struct(attributes)

	// Create default values dynamically
	op = jen.Options{
		Open:  "\n",
		Multi: true,
		Close: "\n",
	}
	defaultValues := jen.CustomFunc(op, func(g *jen.Group) {

		for key, val := range data.Fields {

			switch val.fieldType {
			case "array":
				g.Var().Id(key + "_SET").Index().String()
			case "bool":
				g.Var().Id(key + "_SET").Bool().Op("=").Id(val.fieldDefault)
			case "string":
				g.Var().Id(key + "_SET").String().Op("=").Lit(val.fieldDefault)
			default:

			}

			g.If(jen.List(jen.Id("value"), jen.Id("ok")).Op(":=").Id("fullConfig").Index(jen.Lit(val.fieldYAML)), jen.Id("ok")).Block(
				jen.Id(key + "_SET").Op("=").Id("value"),
			)

		}
	})

	// Create return values dynamically
	op = jen.Options{
		Multi:     true,
		Close:     "\n",
		Separator: ",",
	}
	returnValues := jen.CustomFunc(op, func(g *jen.Group) {

		for key, val := range data.Fields {

			switch val.fieldType {
			case "array":
				g.Id(key).Id(":").Id(key + "_SET")
			case "bool":
				g.Id(key).Id(":").Id(key + "_SET")
			case "string":
				g.Id(key).Id(":").Id(key + "_SET")
			default:

			}

		}
	})

	// Create constructor
	f.Comment("Constructor")
	f.Func().Id("New"+data.FieldGroupName+"FieldGroup").Params(jen.Id("fullConfig").Map(jen.String()).Interface()).Id("FieldGoup").Block(
		defaultValues,
		jen.Return(jen.Op("&").Id(data.FieldGroupName+"FieldGroup").Values(returnValues)),
	)

	// Create Validator function
	f.Comment("Validator Function")
	f.Func().Params(jen.Id("fg *"+data.FieldGroupName+"FieldGroup")).Id("Validate").Params().Params(jen.Bool(), jen.Error()).Block(
		jen.Return(jen.True(), jen.Nil()),
	)

	fmt.Printf("%#v", f)
}
