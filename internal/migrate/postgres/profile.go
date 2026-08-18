package postgres

type columnKind string

const (
	kindInt64     columnKind = "integer"
	kindText      columnKind = "text"
	kindBool      columnKind = "boolean"
	kindTimestamp columnKind = "timestamp"
	kindBytes     columnKind = "bytes"

	alembicVersionTable = "alembic_version"
	postgresTypeDate    = "date"
)

type postgresColumn struct {
	Name         string
	PostgresType string
	Kind         columnKind
}

type postgresTable struct {
	Name    string
	Columns []postgresColumn
}

// postgresProfile defines the frozen PostgreSQL source contract.
// approvedPostgresProfile in profile_generated.go is generated from
// schemaInventorySQL against a disposable OMR v2.0.11 database at its pinned
// schema revision. To update it, provision the newly approved source revision,
// regenerate the sorted table and column literals from that inventory, update
// the fingerprint and profile assertions, and run make go-test-postgres.
type postgresProfile struct {
	SchemaRevision    string
	SchemaFingerprint string
	Tables            []postgresTable
}
