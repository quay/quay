// Package dal adapts repository business storage to sqlc database queries.
package dal

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"

	"github.com/google/uuid"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/repository"
)

const (
	repositoryGCQueueName                 = "repositorygc"
	repositoryGCQueueItemAvailable        = true
	repositoryGCQueueItemRetriesRemaining = 5
)

// Store implements repository.Store with the Quay database.
type Store struct {
	db      *sql.DB
	queries *daldb.Queries
}

var _ repository.Store = (*Store)(nil)

// NewStore returns a SQL-backed repository store.
func NewStore(db *sql.DB) *Store {
	return &Store{db: db, queries: daldb.New(db)}
}

// Get returns repository details for business operations.
func (s *Store) Get(ctx context.Context, ref repository.Ref) (repository.Repository, error) {
	row, err := s.queries.GetRepositoryAccessByNamespaceName(ctx, daldb.GetRepositoryAccessByNamespaceNameParams{
		Username: ref.Namespace,
		Name:     ref.Name,
	})
	if errors.Is(err, sql.ErrNoRows) {
		return repository.Repository{}, repository.ErrNotFound
	}
	if err != nil {
		return repository.Repository{}, err
	}

	return repository.Repository{
		ID: row.ID,
		Ref: repository.Ref{
			Namespace: row.Namespace,
			Name:      row.Name,
		},
		Visibility: repository.Visibility(row.Visibility),
	}, nil
}

// SetVisibility changes a repository visibility value.
func (s *Store) SetVisibility(ctx context.Context, id int64, visibility repository.Visibility) error {
	result, err := s.queries.UpdateRepositoryVisibility(ctx, daldb.UpdateRepositoryVisibilityParams{
		Visibility:   string(visibility),
		RepositoryID: id,
	})
	if err != nil {
		return err
	}
	if err := requireRowsAffected(result); err != nil {
		return err
	}
	return nil
}

// MarkDeleted renames and marks a repository deleted with its deletedrepository marker.
func (s *Store) MarkDeleted(ctx context.Context, repo repository.Repository, deletedName string) (retErr error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() {
		if retErr != nil {
			_ = tx.Rollback()
		}
	}()

	q := s.queries.WithTx(tx)
	if err := q.DeleteStarsByRepository(ctx, repo.ID); err != nil {
		return err
	}

	result, err := q.MarkRepositoryDeleted(ctx, daldb.MarkRepositoryDeletedParams{
		DeletedName:  deletedName,
		RepositoryID: repo.ID,
	})
	if err != nil {
		return err
	}
	if err := requireRowsAffected(result); err != nil {
		return err
	}

	markerID, err := q.InsertDeletedRepository(ctx, daldb.InsertDeletedRepositoryParams{
		RepositoryID: repo.ID,
		OriginalName: repo.Ref.Name,
	})
	if err != nil {
		return err
	}

	body, err := json.Marshal(map[string]any{
		"marker_id":     markerID,
		"original_name": repo.Ref.Name,
	})
	if err != nil {
		return err
	}

	queueID, err := q.InsertRepositoryGCQueueItem(ctx, daldb.InsertRepositoryGCQueueItemParams{
		QueueName:        repositoryGCQueueItemName(repo),
		Body:             string(body),
		Available:        repositoryGCQueueItemAvailable,
		RetriesRemaining: repositoryGCQueueItemRetriesRemaining,
		StateID:          uuid.NewString(),
	})
	if err != nil {
		return err
	}

	if err := q.UpdateDeletedRepositoryQueueID(ctx, daldb.UpdateDeletedRepositoryQueueIDParams{
		ID:      markerID,
		QueueID: sql.NullString{String: strconv.FormatInt(queueID, 10), Valid: true},
	}); err != nil {
		return err
	}

	return tx.Commit()
}

func repositoryGCQueueItemName(repo repository.Repository) string {
	return fmt.Sprintf("%s/%s/%d/", repositoryGCQueueName, repo.Ref.Namespace, repo.ID)
}

func requireRowsAffected(result sql.Result) error {
	rows, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return repository.ErrNotFound
	}
	return nil
}
