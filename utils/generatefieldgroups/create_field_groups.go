package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"strings"

	"github.com/creasty/defaults"
	"github.com/dave/jennifer/jen"
)

type Config struct {
	PackageName string       `json:"packageName"`
	FieldGroups []FieldGroup `json:"fieldGroups"`
}

type FieldGroup struct {
	FieldGroupName string  `json:"fieldGroupName"`
	Fields         []Field `json:"fields"`
}

type Field struct {
	FieldName    string `json:"fieldName"`
	FieldYAML    string `json:"fieldYAML"`
	FieldType    string `json:"fieldType"`
	FieldDefault string `json:"fieldDefault"`
}

func main() {

	newObj := &TagExpirationFieldGroup{}
	defaults.Set(newObj)
	fmt.Printf("%+v\n", newObj)

	return

	// Read config file
	fieldGroupDefinitions, err := ioutil.ReadFile("obj.json")
	if err != nil {
		return
	}

	var config Config

	if err = json.Unmarshal(fieldGroupDefinitions, &config); err != nil {
		fmt.Println("error: " + err.Error())
	}

	packageName := config.PackageName

	for _, fieldGroup := range config.FieldGroups {
		fmt.Println("Creating File for FieldGroup: " + fieldGroup.FieldGroupName)

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

		fmt.Printf("%#v", f)

	}

}

type TagExpirationFieldGroup struct {
	FeatureChangeTagExpiration bool     `default:"false"`
	DefaultTagExpiration       string   `default:"2w"`
	TagExpirationOptions       []string `default:"[\"0s\", \"1d\", \"1w\", \"2w\", \"4w\"]"`
}

// Constructor
func NewTagExpirationFieldGroup(fullConfig map[string]interface{}) *TagExpirationFieldGroup {
	newTagExpiration := &TagExpirationFieldGroup{}
	defaults.Set(newTagExpiration)

	if value, ok := fullConfig["FEATURE_CHANGE_TAG_EXPIRATION"]; ok {
		newTagExpiration.FeatureChangeTagExpiration = value.(bool)
	}
	if value, ok := fullConfig["DEFAULT_TAG_EXPIRATION"]; ok {
		newTagExpiration.DefaultTagExpiration = value.(string)
	}
	if value, ok := fullConfig["TAG_EXPIRATION_OPTIONS"]; ok {
		newTagExpiration.TagExpirationOptions = value.([]string)
	}

	return newTagExpiration
}
