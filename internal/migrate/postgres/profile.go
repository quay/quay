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

type postgresProfile struct {
	SchemaRevision    string
	SchemaFingerprint string
	Tables            []postgresTable
}
