package schema

import _ "embed"

//go:embed quay_schema.sql
var QuaySchemaSQL string

//go:embed seed_data.sql
var SeedDataSQL string
