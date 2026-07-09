# Makefile for the Quay project.

# Define the go-schema target.
go-schema:
	@echo "Generating SQLite schema..."
	@go run internal/dal/schema/sqlite/quay_schema.go -db=$(DB) -output=$(OUTPUT)

# Define the dependencies for the go-schema target.
go-schema-deps:
	@echo "Installing dependencies..."
	@go get -u github.com/quay/quay/db

# Define the clean target.
clean:
	@echo "Cleaning up..."
	@rm -f quay_schema.sql

# Define the default target.
default: go-schema-deps go-schema clean