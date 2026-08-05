// Package repository registers repository API v1 endpoints.
package repository

import (
	"context"
	"errors"
	"log/slog"
	"net/http"

	apiv1 "github.com/quay/quay/internal/api/v1"
	"github.com/quay/quay/internal/auth"
	repomodel "github.com/quay/quay/internal/repository"
)

const (
	repositoryPathPrefix = "/api/v1/repository/"
	repositoryParamName  = "repository"
)

// Service provides repository business operations used by API handlers.
type Service interface {
	Delete(ctx context.Context, principal *auth.Principal, ref repomodel.Ref) error
}

// Module registers repository API endpoints.
type Module struct {
	service Service
}

// NewModule returns a selectable repository API module.
func NewModule(service Service) Module {
	return Module{service: service}
}

// Register registers repository API routes.
func (m Module) Register(router *apiv1.Router) {
	router.Handle(
		http.MethodDelete,
		repositoryPath(),
		router.RequireBasic(m.deleteRepository),
	)
}

func (m Module) deleteRepository(w http.ResponseWriter, r *http.Request, params apiv1.Params, principal *auth.Principal) {
	namespace := params["namespace"]
	repositoryName := params[repositoryParamName]

	err := m.service.Delete(
		r.Context(),
		principal,
		repomodel.Ref{Namespace: namespace, Name: repositoryName},
	)
	if err != nil {
		switch {
		case errors.Is(err, repomodel.ErrNotFound):
			apiv1.WriteError(w, http.StatusNotFound, "repository not found")
		case errors.Is(err, repomodel.ErrForbidden):
			apiv1.WriteError(w, http.StatusForbidden, "forbidden")
		default:
			slog.Error("repository delete failed", "namespace", namespace, "repository", repositoryName, "err", err)
			apiv1.WriteError(w, http.StatusInternalServerError, "repository delete failed")
		}
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func repositoryPath() apiv1.Matcher {
	return apiv1.RepositoryPath(repositoryParamName, repositoryPathPrefix, "")
}
