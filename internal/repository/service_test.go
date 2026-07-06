package repository

import (
	"context"
	"errors"
	"testing"

	"github.com/quay/quay/internal/auth"
)

type fakeStore struct {
	repo          Repository
	getErr        error
	setID         int64
	setVisibility Visibility
	setErr        error
	setCalled     bool
	deletedRepo   Repository
	deletedName   string
	deleteErr     error
	deleteCalled  bool
}

func (s *fakeStore) Get(context.Context, Ref) (Repository, error) {
	if s.getErr != nil {
		return Repository{}, s.getErr
	}
	return s.repo, nil
}

func (s *fakeStore) SetVisibility(_ context.Context, id int64, visibility Visibility) error {
	s.setCalled = true
	s.setID = id
	s.setVisibility = visibility
	return s.setErr
}

func (s *fakeStore) MarkDeleted(_ context.Context, repo Repository, deletedName string) error {
	s.deleteCalled = true
	s.deletedRepo = repo
	s.deletedName = deletedName
	return s.deleteErr
}

type fakeAuthorizer struct {
	allowed bool
	err     error
}

func (a fakeAuthorizer) CanAdminRepository(context.Context, *auth.Principal, Repository) (bool, error) {
	return a.allowed, a.err
}

func TestServiceChangeVisibility(t *testing.T) {
	store := &fakeStore{
		repo: Repository{
			ID: 7,
			Ref: Ref{
				Namespace: "devtable",
				Name:      "repo",
			},
			Visibility: VisibilityPrivate,
		},
	}
	service, err := NewService(store, fakeAuthorizer{allowed: true})
	if err != nil {
		t.Fatalf("new service: %v", err)
	}

	err = service.ChangeVisibility(
		t.Context(),
		&auth.Principal{Username: "devtable", Kind: auth.PrincipalUser},
		Ref{Namespace: "devtable", Name: "repo"},
		VisibilityPublic,
	)
	if err != nil {
		t.Fatalf("change visibility: %v", err)
	}
	if !store.setCalled {
		t.Fatal("expected SetVisibility call")
	}
	if store.setID != 7 {
		t.Fatalf("set ID = %d, want 7", store.setID)
	}
	if store.setVisibility != VisibilityPublic {
		t.Fatalf("set visibility = %q, want public", store.setVisibility)
	}
}

func TestServiceChangeVisibilityInvalidVisibility(t *testing.T) {
	store := &fakeStore{}
	service, err := NewService(store, fakeAuthorizer{allowed: true})
	if err != nil {
		t.Fatalf("new service: %v", err)
	}

	err = service.ChangeVisibility(t.Context(), &auth.Principal{Username: "devtable", Kind: auth.PrincipalUser}, Ref{Namespace: "devtable", Name: "repo"}, Visibility("internal"))
	if !errors.Is(err, ErrInvalidVisibility) {
		t.Fatalf("err = %v, want ErrInvalidVisibility", err)
	}
	if store.setCalled {
		t.Fatal("SetVisibility should not be called")
	}
}

func TestServiceChangeVisibilityForbidden(t *testing.T) {
	store := &fakeStore{
		repo: Repository{
			ID: 7,
			Ref: Ref{
				Namespace: "devtable",
				Name:      "repo",
			},
		},
	}
	service, err := NewService(store, fakeAuthorizer{allowed: false})
	if err != nil {
		t.Fatalf("new service: %v", err)
	}

	err = service.ChangeVisibility(t.Context(), &auth.Principal{Username: "reader", Kind: auth.PrincipalUser}, Ref{Namespace: "devtable", Name: "repo"}, VisibilityPublic)
	if !errors.Is(err, ErrForbidden) {
		t.Fatalf("err = %v, want ErrForbidden", err)
	}
	if store.setCalled {
		t.Fatal("SetVisibility should not be called")
	}
}

func TestServiceDelete(t *testing.T) {
	store := &fakeStore{
		repo: Repository{
			ID: 7,
			Ref: Ref{
				Namespace: "devtable",
				Name:      "repo",
			},
		},
	}
	service, err := NewService(store, fakeAuthorizer{allowed: true})
	if err != nil {
		t.Fatalf("new service: %v", err)
	}

	err = service.Delete(t.Context(), &auth.Principal{Username: "devtable", Kind: auth.PrincipalUser}, Ref{Namespace: "devtable", Name: "repo"})
	if err != nil {
		t.Fatalf("delete: %v", err)
	}
	if !store.deleteCalled {
		t.Fatal("expected MarkDeleted call")
	}
	if store.deletedRepo.ID != 7 {
		t.Fatalf("deleted repo ID = %d, want 7", store.deletedRepo.ID)
	}
	if store.deletedName == "" || store.deletedName == "repo" {
		t.Fatalf("deleted name = %q, want generated name", store.deletedName)
	}
}

func TestServiceDeleteForbidden(t *testing.T) {
	store := &fakeStore{
		repo: Repository{
			ID: 7,
			Ref: Ref{
				Namespace: "devtable",
				Name:      "repo",
			},
		},
	}
	service, err := NewService(store, fakeAuthorizer{allowed: false})
	if err != nil {
		t.Fatalf("new service: %v", err)
	}

	err = service.Delete(t.Context(), &auth.Principal{Username: "reader", Kind: auth.PrincipalUser}, Ref{Namespace: "devtable", Name: "repo"})
	if !errors.Is(err, ErrForbidden) {
		t.Fatalf("err = %v, want ErrForbidden", err)
	}
	if store.deleteCalled {
		t.Fatal("MarkDeleted should not be called")
	}
}
