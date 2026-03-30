package schema

import _ "embed"

//go:embed sqlite/quay_schema.sql
var QuaySchemaSQL string

//go:embed sqlite/seed_data.sql
var SeedDataSQL string
