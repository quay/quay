package internal

import (
	"database/sql"
	"fmt"
	"log"
	"sort"

	"github.com/quay/quay/db"
)

// TableMetadata represents a table's metadata.
type TableMetadata struct {
	Name string
	// Indexes is a list of indexes on this table.
	Indexes []*IndexMetadata
}

// IndexMetadata represents an index's metadata.
type IndexMetadata struct {
	Name string
}

// getTableMetadata retrieves the table metadata from the database.
func getTableMetadata(db *sql.DB) ([]TableMetadata, error) {
	// Implement the logic to retrieve the table metadata from the database.
	return nil, nil
}

// sortTableMetadata sorts the table metadata by index name.
func sortTableMetadata(metadata []TableMetadata) {
	sort.Slice(metadata, func(i, j int) bool {
		return metadata[i].Name < metadata[j].Name
	})
}