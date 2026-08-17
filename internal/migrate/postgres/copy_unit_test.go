package postgres

import (
	"testing"
	"time"
)

func TestConvertColumnValue(t *testing.T) {
	ts := time.Date(2026, 7, 31, 12, 36, 42, 332282000, time.UTC)
	tests := []struct {
		name string
		col  postgresColumn
		in   any
		want any
	}{
		{"int64 passthrough", postgresColumn{kind: kindInt64}, int64(42), int64(42)},
		{"int32 widened", postgresColumn{kind: kindInt64}, int32(7), int64(7)},
		{"text passthrough", postgresColumn{kind: kindText}, "hello", "hello"},
		{"text preserves sql-looking words", postgresColumn{kind: kindText}, "true; DROP TABLE user", "true; DROP TABLE user"},
		{"bool true becomes 1", postgresColumn{kind: kindBool}, true, int64(1)},
		{"bool false becomes 0", postgresColumn{kind: kindBool}, false, int64(0)},
		{"timestamp with fraction", postgresColumn{kind: kindTimestamp}, ts, "2026-07-31 12:36:42.332282"},
		{"timestamp without fraction", postgresColumn{kind: kindTimestamp}, time.Date(2026, 7, 31, 12, 36, 42, 0, time.UTC), "2026-07-31 12:36:42"},
		{"null int", postgresColumn{kind: kindInt64}, nil, nil},
		{"null text", postgresColumn{kind: kindText}, nil, nil},
		{"null bool", postgresColumn{kind: kindBool}, nil, nil},
		{"null timestamp", postgresColumn{kind: kindTimestamp}, nil, nil},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := convertColumnValue(tc.col, tc.in)
			if err != nil {
				t.Fatalf("convertColumnValue: %v", err)
			}
			if got != tc.want {
				t.Errorf("convertColumnValue(%v, %v) = %v (%T), want %v (%T)", tc.col.kind, tc.in, got, got, tc.want, tc.want)
			}
		})
	}
}

func TestConvertColumnValueRejectsTypeMismatch(t *testing.T) {
	tests := []struct {
		name string
		col  postgresColumn
		in   any
	}{
		{"int64 given string", postgresColumn{kind: kindInt64}, "42"},
		{"text given int", postgresColumn{kind: kindText}, int64(1)},
		{"bool given int", postgresColumn{kind: kindBool}, int64(1)},
		{"timestamp given string", postgresColumn{kind: kindTimestamp}, "2026-07-31 12:36:42"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := convertColumnValue(tc.col, tc.in); err == nil {
				t.Fatalf("convertColumnValue(%v, %v) unexpectedly succeeded", tc.col.kind, tc.in)
			}
		})
	}
}

func TestApprovedProfileForeignKeyOrder(t *testing.T) {
	order := make(map[string]int, len(approvedPostgresTables))
	for i, table := range approvedPostgresTables {
		order[table.name] = i
	}

	requireBefore := func(first, second string) {
		t.Helper()
		firstIndex, ok := order[first]
		if !ok {
			t.Fatalf("table %q not in approved profile", first)
		}
		secondIndex, ok := order[second]
		if !ok {
			t.Fatalf("table %q not in approved profile", second)
		}
		if firstIndex >= secondIndex {
			t.Errorf("expected %q before %q", first, second)
		}
	}

	requireBefore("visibility", "repository")
	requireBefore("repositorykind", "repository")
	requireBefore("mediatype", "manifest")
	requireBefore("tagkind", "tag")
	requireBefore("user", "repository")
	requireBefore("repository", "manifest")
	requireBefore("repository", "tag")
	requireBefore("manifest", "tag")
}

func TestApprovedProfileReplacesLookupSeedsOnly(t *testing.T) {
	wantReplaces := map[string]bool{
		"visibility": true, "repositorykind": true, "mediatype": true, "tagkind": true,
		"user": false, "repository": false, "manifest": false, "tag": false,
	}

	seen := make(map[string]bool, len(approvedPostgresTables))
	for _, table := range approvedPostgresTables {
		seen[table.name] = true
		want, ok := wantReplaces[table.name]
		if !ok {
			t.Fatalf("table %q is missing an expectation", table.name)
		}
		if table.replacesBaselineSeed != want {
			t.Errorf("table %q replacesBaselineSeed = %v, want %v", table.name, table.replacesBaselineSeed, want)
		}
	}
	for name := range wantReplaces {
		if !seen[name] {
			t.Errorf("table %q is missing from approved profile", name)
		}
	}
}
