package cmd

import (
	"context"
	"crypto/rand"
	"database/sql"
	"flag"
	"fmt"
	"os"

	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
)

func runUser(args []string) int {
	if len(args) == 0 {
		userUsage()
		return 1
	}

	switch args[0] {
	case "create":
		return runUserCreate(args[1:])
	case "help", "-h", "--help":
		userUsage()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown user command: %s\n", args[0])
		userUsage()
		return 1
	}
}

func userUsage() {
	fmt.Fprintln(os.Stderr, `usage: quay user <command> [flags]

commands:
  create            Create a new user in the database`)
}

func runUserCreate(args []string) int {
	fs := flag.NewFlagSet("user create", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml")
	username := fs.String("username", "", "username (required)")
	email := fs.String("email", "", "email address (required)")
	password := fs.String("password", "", "password (required)")
	if err := fs.Parse(args); err != nil {
		return 1
	}

	if *username == "" || *email == "" || *password == "" {
		fmt.Fprintln(os.Stderr, "error: --username, --email, and --password are required")
		fs.Usage()
		return 1
	}

	dbPath, err := loadDBPath(resolveConfigPath(*configPath))
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	defer db.Close()

	hash, err := bcrypt.GenerateFromPassword([]byte(*password), bcrypt.DefaultCost)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error hashing password: %v\n", err)
		return 1
	}

	uuid, err := generateUUID()
	if err != nil {
		fmt.Fprintf(os.Stderr, "error generating UUID: %v\n", err)
		return 1
	}

	queries := daldb.New(db)
	ctx := context.Background()

	id, err := queries.CreateAdminUser(ctx, daldb.CreateAdminUserParams{
		Uuid:         sql.NullString{String: uuid, Valid: true},
		Username:     *username,
		PasswordHash: sql.NullString{String: string(hash), Valid: true},
		Email:        *email,
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "error creating user: %v\n", err)
		return 1
	}

	fmt.Fprintf(os.Stdout, "Created user %q (id=%d)\n", *username, id)
	return 0
}

// generateUUID creates a UUID v4 using crypto/rand.
func generateUUID() (string, error) {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", err
	}
	b[6] = (b[6] & 0x0f) | 0x40 // version 4
	b[8] = (b[8] & 0x3f) | 0x80 // variant 10
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:16]), nil
}
