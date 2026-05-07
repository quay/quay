package cmd

import (
	"context"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
)

// runDBPublic handles the user-facing "quay db" subcommand (version only).
func runDBPublic(args []string) int {
	if len(args) == 0 {
		dbPublicUsage()
		return 1
	}

	switch args[0] {
	case versionLiteral:
		return runDBVersion(args[1:])
	case helpLiteral, "-h", helpFlag:
		dbPublicUsage()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown db command: %s\n", args[0])
		dbPublicUsage()
		return 1
	}
}

// runDB handles the internal "_db" subcommand (init, version, upgrade).
func runDB(args []string) int {
	if len(args) == 0 {
		dbUsage()
		return 1
	}

	switch args[0] {
	case "init":
		return runDBInit(args[1:])
	case versionLiteral:
		return runDBVersion(args[1:])
	case "upgrade":
		return runDBUpgrade(args[1:])
	case helpLiteral, "-h", helpFlag:
		dbUsage()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown db command: %s\n", args[0])
		dbUsage()
		return 1
	}
}

func dbPublicUsage() {
	fmt.Fprintln(os.Stderr, `usage: quay db <command> [flags]

commands:
  version           Print the current schema version`)
}

func dbUsage() {
	fmt.Fprintln(os.Stderr, `usage: quay _db <command> [flags]

commands:
  init              Create a fresh SQLite database with schema and seed data
  version           Print the current schema version
  upgrade           Apply pending schema migrations`)
}

// loadDBPath reads the config and extracts the SQLite file path from DB_URI.
// Relative paths are resolved against the config file's directory so the same
// config works inside the container (/data/config.yaml → /data/quay.db) and
// on the host (/var/lib/quay/config.yaml → /var/lib/quay/quay.db).
func loadDBPath(configPath string) (string, error) {
	cfg, err := config.Load(configPath)
	if err != nil {
		return "", fmt.Errorf("load config: %w", err)
	}

	if cfg.DBURI == "" {
		return "", fmt.Errorf("DB_URI not set in config")
	}

	if !strings.HasPrefix(cfg.DBURI, "sqlite:///") {
		return "", fmt.Errorf("DB_URI must start with sqlite:/// for db commands (got %s)", cfg.DBURI)
	}

	dbPath := strings.TrimPrefix(cfg.DBURI, "sqlite:///")

	if !filepath.IsAbs(dbPath) {
		dbPath = filepath.Join(filepath.Dir(configPath), dbPath)
	}

	return dbPath, nil
}

// resolveConfigPath returns the config path from the flag, QUAY_CONFIG env, or default.
func resolveConfigPath(flagValue string) string {
	if flagValue != "" {
		return flagValue
	}
	if env := os.Getenv("QUAY_CONFIG"); env != "" {
		return env
	}
	return "config.yaml"
}

func runDBInit(args []string) int {
	fs := flag.NewFlagSet("db init", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (default: $QUAY_CONFIG or ./config.yaml)")
	if err := fs.Parse(args); err != nil {
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
	defer func() { _ = db.Close() }()

	ctx := context.Background()
	if err := dbcore.InitDatabase(ctx, db, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	fmt.Fprintf(os.Stdout, "Database: %s\n", dbPath)
	return 0
}

func runDBVersion(args []string) int {
	fs := flag.NewFlagSet("db version", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (default: $QUAY_CONFIG or ./config.yaml)")
	if err := fs.Parse(args); err != nil {
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
	defer func() { _ = db.Close() }()

	ver, err := dbcore.SchemaVersion(context.Background(), db)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	if ver == "" {
		fmt.Fprintln(os.Stdout, "no schema version found (database may be uninitialized)")
		return 0
	}

	fmt.Fprintf(os.Stdout, "Schema version: %s\n", ver)
	return 0
}

func runDBUpgrade(args []string) int {
	fs := flag.NewFlagSet("db upgrade", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (default: $QUAY_CONFIG or ./config.yaml)")
	dryRun := fs.Bool("dry-run", false, "preview migrations without applying")
	if err := fs.Parse(args); err != nil {
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
	defer func() { _ = db.Close() }()

	ctx := context.Background()

	ver, err := dbcore.SchemaVersion(ctx, db)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	if ver == "" {
		fmt.Fprintln(os.Stderr, "error: database has no schema version; use 'quay db init' first")
		return 1
	}

	// Check if the database is already at the target version.
	if ver == dbcore.TargetVersion {
		if *dryRun {
			fmt.Fprintf(os.Stdout, "Current version: %s\nNo pending migrations.\n", ver)
		} else {
			fmt.Fprintf(os.Stdout, "Schema version: %s (up to date)\n", ver)
		}
		return 0
	}

	// Version mismatch — database needs upgrading.
	if *dryRun {
		fmt.Fprintf(os.Stdout, "Current version: %s\nTarget version:  %s\n", ver, dbcore.TargetVersion)
		// TODO: List pending migration files when they exist.
		return 0
	}

	// Backup before any upgrade attempt.
	backupPath, err := dbcore.BackupDatabase(ctx, db, dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error creating backup: %v\n", err)
		return 1
	}
	fmt.Fprintf(os.Stdout, "Backup: %s\n", backupPath)

	// Verify integrity after backup.
	if err := dbcore.IntegrityCheck(ctx, db); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// TODO: Apply migration chain here once migration files are generated.
	// For now, fail if the version doesn't match — migrations are not yet available.
	fmt.Fprintf(os.Stderr, "error: database version %s does not match binary version %s\n", ver, dbcore.TargetVersion)
	fmt.Fprintln(os.Stderr, "migration files not yet available for this version transition")

	// Clean old backups, keep last 3.
	_ = dbcore.CleanOldBackups(dbPath, 3)

	return 1
}
