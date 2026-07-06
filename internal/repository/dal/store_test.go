package dal

import (
	"database/sql"
	"errors"
	"testing"

	"github.com/quay/quay/internal/repository"
)

type fakeResult struct {
	rowsAffected    int64
	rowsAffectedErr error
}

var _ sql.Result = fakeResult{}

func (r fakeResult) LastInsertId() (int64, error) {
	return 0, nil
}

func (r fakeResult) RowsAffected() (int64, error) {
	return r.rowsAffected, r.rowsAffectedErr
}

func TestRequireRowsAffected(t *testing.T) {
	sentinelErr := errors.New("rows affected unavailable")

	for _, tc := range []struct {
		name    string
		result  sql.Result
		wantErr error
	}{
		{
			name:    "driver error",
			result:  fakeResult{rowsAffectedErr: sentinelErr},
			wantErr: sentinelErr,
		},
		{
			name:    "no rows",
			result:  fakeResult{rowsAffected: 0},
			wantErr: repository.ErrNotFound,
		},
		{
			name:   "changed rows",
			result: fakeResult{rowsAffected: 1},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			err := requireRowsAffected(tc.result)
			if !errors.Is(err, tc.wantErr) {
				t.Fatalf("err = %v, want %v", err, tc.wantErr)
			}
		})
	}
}
