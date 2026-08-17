package postgres

import (
	"reflect"
	"sort"
	"strings"
	"testing"
	"time"
)

func TestConvertColumnValue(t *testing.T) {
	timestamp := time.Date(2026, 7, 31, 12, 36, 42, 332282000, time.UTC)
	binary := []byte{0, 1, 2, 255}
	tests := []struct {
		name   string
		column postgresColumn
		input  any
		want   any
	}{
		{"int64 passthrough", postgresColumn{Kind: kindInt64}, int64(42), int64(42)},
		{"int32 widened", postgresColumn{Kind: kindInt64}, int32(7), int64(7)},
		{"text passthrough", postgresColumn{Kind: kindText}, "hello", "hello"},
		{"text preserves sql-looking words", postgresColumn{Kind: kindText}, "true; DROP TABLE user", "true; DROP TABLE user"},
		{"bool true becomes 1", postgresColumn{Kind: kindBool}, true, int64(1)},
		{"bool false becomes 0", postgresColumn{Kind: kindBool}, false, int64(0)},
		{"timestamp with fraction", postgresColumn{Kind: kindTimestamp}, timestamp, "2026-07-31 12:36:42.332282"},
		{"timestamp without fraction", postgresColumn{Kind: kindTimestamp}, time.Date(2026, 7, 31, 12, 36, 42, 0, time.UTC), "2026-07-31 12:36:42"},
		{"date", postgresColumn{PostgresType: postgresTypeDate, Kind: kindTimestamp}, timestamp, "2026-07-31"},
		{"bytes", postgresColumn{Kind: kindBytes}, binary, binary},
		{"null integer", postgresColumn{Kind: kindInt64}, nil, nil},
		{"null text", postgresColumn{Kind: kindText}, nil, nil},
		{"null boolean", postgresColumn{Kind: kindBool}, nil, nil},
		{"null timestamp", postgresColumn{Kind: kindTimestamp}, nil, nil},
		{"null bytes", postgresColumn{Kind: kindBytes}, nil, nil},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			got, err := convertColumnValue(test.column, test.input)
			if err != nil {
				t.Fatalf("convertColumnValue: %v", err)
			}
			if !reflect.DeepEqual(got, test.want) {
				t.Errorf("convertColumnValue(%v, %v) = %v (%T), want %v (%T)", test.column.Kind, test.input, got, got, test.want, test.want)
			}
		})
	}
}

func TestConvertColumnValueRejectsTypeMismatch(t *testing.T) {
	tests := []struct {
		name   string
		column postgresColumn
		input  any
	}{
		{"integer given string", postgresColumn{Kind: kindInt64}, "42"},
		{"text given integer", postgresColumn{Kind: kindText}, int64(1)},
		{"boolean given integer", postgresColumn{Kind: kindBool}, int64(1)},
		{"timestamp given string", postgresColumn{Kind: kindTimestamp}, "2026-07-31 12:36:42"},
		{"bytes given string", postgresColumn{Kind: kindBytes}, "not bytes"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if _, err := convertColumnValue(test.column, test.input); err == nil {
				t.Fatalf("convertColumnValue(%v, %v) unexpectedly succeeded", test.column.Kind, test.input)
			}
		})
	}
}

func TestSchemaFingerprintIncludesRelationKindAndLogicalOrder(t *testing.T) {
	base := []schemaColumn{{
		table: "example", relationKind: "r", logicalOrdinal: 1,
		name: "id", postgresType: "integer", notNull: true,
	}}
	partitioned := append([]schemaColumn(nil), base...)
	partitioned[0].relationKind = "p"
	reordered := append([]schemaColumn(nil), base...)
	reordered[0].logicalOrdinal = 2

	baseFingerprint := schemaFingerprint(base)
	if schemaFingerprint(partitioned) == baseFingerprint {
		t.Error("relation kind did not affect schema fingerprint")
	}
	if schemaFingerprint(reordered) == baseFingerprint {
		t.Error("logical column order did not affect schema fingerprint")
	}
}

func TestApprovedPostgresProfile(t *testing.T) {
	if approvedPostgresProfile.SchemaRevision != "3f8d7acdf7f9" {
		t.Errorf("schema revision = %q", approvedPostgresProfile.SchemaRevision)
	}
	const wantFingerprint = "176e0e0b4bed6f6325343a3c206103ed004f2038205885903a523f69e5bd8b07"
	if approvedPostgresProfile.SchemaFingerprint != wantFingerprint {
		t.Errorf("schema fingerprint = %q, want %q", approvedPostgresProfile.SchemaFingerprint, wantFingerprint)
	}
	if len(approvedPostgresProfile.Tables) != 96 {
		t.Fatalf("profile table count = %d, want 96", len(approvedPostgresProfile.Tables))
	}

	var columnCount int
	tableNames := make([]string, 0, len(approvedPostgresProfile.Tables))
	for _, table := range approvedPostgresProfile.Tables {
		if table.Name == alembicVersionTable {
			t.Error("alembic_version must be validated, not copied")
		}
		tableNames = append(tableNames, table.Name)
		for _, column := range table.Columns {
			columnCount++
			if want := expectedKind(column.PostgresType); column.Kind != want {
				t.Errorf("%s.%s kind = %q, want %q for %q", table.Name, column.Name, column.Kind, want, column.PostgresType)
			}
		}
	}
	if columnCount != 527 {
		t.Errorf("profile column count = %d, want 527", columnCount)
	}
	if !sort.StringsAreSorted(tableNames) {
		t.Error("profile tables are not deterministically sorted")
	}
}

func expectedKind(postgresType string) columnKind {
	switch {
	case postgresType == "smallint", postgresType == "integer", postgresType == "bigint":
		return kindInt64
	case postgresType == "boolean":
		return kindBool
	case postgresType == "text", strings.HasPrefix(postgresType, "character varying"):
		return kindText
	case postgresType == "timestamp without time zone", postgresType == postgresTypeDate:
		return kindTimestamp
	case postgresType == "bytea":
		return kindBytes
	default:
		return ""
	}
}
