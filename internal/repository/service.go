package repository

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/quay/quay/internal/auth"
)

// Store persists repository state.
type Store interface {
	Get(ctx context.Context, ref Ref) (Repository, error)
	SetVisibility(ctx context.Context, id int64, visibility Visibility) error
	MarkDeleted(ctx context.Context, repo Repository, deletedName string) error
}

// Authorizer decides whether an actor can perform repository operations.
type Authorizer interface {
	CanAdminRepository(ctx context.Context, principal *auth.Principal, repo Repository) (bool, error)
}

// Service implements repository business operations.
type Service struct {
	store      Store
	authorizer Authorizer
}

// NewService returns a repository service.
func NewService(store Store, authorizer Authorizer) (*Service, error) {
	if store == nil {
		return nil, fmt.Errorf("nil repository store")
	}
	if authorizer == nil {
		return nil, fmt.Errorf("nil repository authorizer")
	}
	return &Service{store: store, authorizer: authorizer}, nil
}

// ChangeVisibility changes a repository visibility after validation and authorization.
func (s *Service) ChangeVisibility(ctx context.Context, principal *auth.Principal, ref Ref, visibility Visibility) error {
	if !visibility.Valid() {
		return ErrInvalidVisibility
	}

	repo, err := s.getAuthorized(ctx, principal, ref)
	if err != nil {
		return err
	}

	return s.store.SetVisibility(ctx, repo.ID, visibility)
}

// Delete marks a repository for deletion after authorization.
//
// This is the minimal standalone Go equivalent of Python's repository delete:
// it frees the original name by renaming the repository, marks it deleted, and
// records a deletedrepository marker with queued repository GC work.
func (s *Service) Delete(ctx context.Context, principal *auth.Principal, ref Ref) error {
	repo, err := s.getAuthorized(ctx, principal, ref)
	if err != nil {
		return err
	}

	return s.store.MarkDeleted(ctx, repo, uuid.NewString())
}

func (s *Service) getAuthorized(ctx context.Context, principal *auth.Principal, ref Ref) (Repository, error) {
	repo, err := s.store.Get(ctx, ref)
	if err != nil {
		return Repository{}, err
	}

	allowed, err := s.authorizer.CanAdminRepository(ctx, principal, repo)
	if err != nil {
		return Repository{}, err
	}
	if !allowed {
		return Repository{}, ErrForbidden
	}

	return repo, nil
}
