package db

import (
	"database/sql"
	"fmt"
	"log"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func TestConnect(t *testing.T) {
	// Connect to the database.
	db, err := Connect(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	// Create a table.
	if _, err := db.Exec(`CREATE TABLE test (id INTEGER PRIMARY KEY)"); err != nil {
		t.Fatal(err)
	}

	// Check that the table exists.
	var count int
	if err := db.QueryRow(`SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='test'`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Errorf("expected 1, got %d", count)
	}
}