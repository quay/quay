package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	"github.com/quay/quay/db"
)

func main() {
	// Connect to the database.
	db, err := db.Connect(os.Getenv("DB_URL"))
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Generate the SQLite schema.
	if err := generateSchema(db); err != nil {
		log.Fatal(err)
	}

	// Write the schema to the output file.
	if err := writeSchema(db); err != nil {
		log.Fatal(err)
	}
}