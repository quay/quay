package dbcore

import (
	"database/sql"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func TestOpenSQLite_OpensExactPathWithReservedCharacters(t *testing.T) {
	filenames := []string{
		"question?.db",
		"encoded%2Fslash.db",
		"hash#.db",
		"space name.db",
		"reserved :[]@!$&'()+,;=.db",
	}

	for _, filename := range filenames {
		t.Run(filename, func(t *testing.T) {
			dbPath := filepath.Join(t.TempDir(), filename)
			db, err := OpenSQLite(dbPath)
			require.NoError(t, err)
			t.Cleanup(func() { _ = db.Close() })

			_, err = db.ExecContext(t.Context(), `CREATE TABLE marker (value INTEGER NOT NULL)`)
			require.NoError(t, err)
			require.NoError(t, db.Close())

			info, err := os.Stat(dbPath)
			require.NoError(t, err)
			require.False(t, info.IsDir())

			reopenedDB, err := OpenSQLite(dbPath)
			require.NoError(t, err)
			t.Cleanup(func() { _ = reopenedDB.Close() })

			var markerTables int
			err = reopenedDB.QueryRowContext(t.Context(),
				`SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'marker'`,
			).Scan(&markerTables)
			require.NoError(t, err)
			require.Equal(t, 1, markerTables)

			var foreignKeys, busyTimeout, synchronous, walAutocheckpoint int
			var journalMode string
			require.NoError(t, reopenedDB.QueryRowContext(t.Context(), `PRAGMA foreign_keys`).Scan(&foreignKeys))
			require.NoError(t, reopenedDB.QueryRowContext(t.Context(), `PRAGMA journal_mode`).Scan(&journalMode))
			require.NoError(t, reopenedDB.QueryRowContext(t.Context(), `PRAGMA busy_timeout`).Scan(&busyTimeout))
			require.NoError(t, reopenedDB.QueryRowContext(t.Context(), `PRAGMA synchronous`).Scan(&synchronous))
			require.NoError(t, reopenedDB.QueryRowContext(t.Context(), `PRAGMA wal_autocheckpoint`).Scan(&walAutocheckpoint))
			require.Equal(t, 1, foreignKeys)
			require.Equal(t, "wal", journalMode)
			require.Equal(t, 10000, busyTimeout)
			require.Equal(t, 1, synchronous)
			require.Equal(t, 1000, walAutocheckpoint)
		})
	}
}

func TestOpenSQLite_SerializesWriteTransactionsAcrossHandles(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "locking ?%# &.db")
	firstDB, err := OpenSQLite(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, firstDB.Close()) })

	secondDB, err := OpenSQLite(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, secondDB.Close()) })

	ctx := t.Context()
	_, err = firstDB.ExecContext(ctx, `CREATE TABLE counter (value INTEGER NOT NULL)`)
	require.NoError(t, err)
	_, err = firstDB.ExecContext(ctx, `INSERT INTO counter (value) VALUES (0)`)
	require.NoError(t, err)

	firstTx, err := firstDB.BeginTx(ctx, nil)
	require.NoError(t, err)
	t.Cleanup(func() { _ = firstTx.Rollback() })

	var value int
	require.NoError(t, firstTx.QueryRowContext(ctx, `SELECT value FROM counter`).Scan(&value))
	require.Equal(t, 0, value)
	_, err = firstTx.ExecContext(ctx, `UPDATE counter SET value = 1`)
	require.NoError(t, err)

	type beginResult struct {
		tx  *sql.Tx
		err error
	}
	beginResultCh := make(chan beginResult, 1)
	require.Zero(t, secondDB.Stats().InUse)
	go func() {
		tx, err := secondDB.BeginTx(ctx, nil)
		beginResultCh <- beginResult{tx: tx, err: err}
	}()
	require.Eventually(t, func() bool {
		return secondDB.Stats().InUse == 1
	}, time.Second, time.Millisecond, "second connection was not checked out by BeginTx")

	select {
	case result := <-beginResultCh:
		if result.tx != nil {
			_ = result.tx.Rollback()
		}
		require.FailNow(t, "second BeginTx returned while the first transaction held the writer lock", "error: %v", result.err)
	case <-time.After(100 * time.Millisecond):
	}

	require.NoError(t, firstTx.Commit())

	var secondTx *sql.Tx
	select {
	case result := <-beginResultCh:
		require.NoError(t, result.err)
		secondTx = result.tx
	case <-time.After(2 * time.Second):
		require.FailNow(t, "second BeginTx did not proceed after the first transaction committed")
	}
	require.NotNil(t, secondTx)
	t.Cleanup(func() { _ = secondTx.Rollback() })

	require.NoError(t, secondTx.QueryRowContext(ctx, `SELECT value FROM counter`).Scan(&value))
	require.Equal(t, 1, value)
	_, err = secondTx.ExecContext(ctx, `UPDATE counter SET value = 2`)
	require.NoError(t, err)
	require.NoError(t, secondTx.Commit())
	require.Eventually(t, func() bool {
		return secondDB.Stats().InUse == 0
	}, time.Second, time.Millisecond, "second transaction did not release its connection")

	require.NoError(t, firstDB.QueryRowContext(ctx, `SELECT value FROM counter`).Scan(&value))
	require.Equal(t, 2, value)
}
