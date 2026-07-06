// Package repository registers repository API v1 endpoints.
package repository

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"

	apiv1 "github.com/quay/quay/internal/api/v1"
	"github.com/quay/quay/internal/auth"
	repomodel "github.com/quay/quay/internal/repository"
)

const (
	changeVisibilityPathPrefix      = "/api/v1/repository/"
	changeVisibilityPathSuffix      = "/changevisibility"
	changeVisibilityRequestMaxBytes = 1024
	repositoryParamName             = "repository"
)

// Service provides repository business operations used by API handlers.
type Service interface {
	ChangeVisibility(ctx context.Context, principal *auth.Principal, ref repomodel.Ref, visibility repomodel.Visibility) error
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
		http.MethodPost,
		apiv1.RepositoryPath(repositoryParamName, changeVisibilityPathPrefix, changeVisibilityPathSuffix),
		router.RequireBasic(m.changeVisibility),
	)
	router.Handle(
		http.MethodDelete,
		repositoryPath(),
		router.RequireBasic(m.deleteRepository),
	)
}

func (m Module) changeVisibility(w http.ResponseWriter, r *http.Request, params apiv1.Params, principal *auth.Principal) {
	namespace := params["namespace"]
	repositoryName := params[repositoryParamName]

	var req struct {
		Visibility string `json:"visibility"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, changeVisibilityRequestMaxBytes)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		var maxBytesErr *http.MaxBytesError
		if errors.As(err, &maxBytesErr) {
			apiv1.WriteError(w, http.StatusRequestEntityTooLarge, "request body too large")
			return
		}
		apiv1.WriteError(w, http.StatusBadRequest, "invalid json")
		return
	}

	err := m.service.ChangeVisibility(
		r.Context(),
		principal,
		repomodel.Ref{Namespace: namespace, Name: repositoryName},
		repomodel.Visibility(req.Visibility),
	)
	if err != nil {
		switch {
		case errors.Is(err, repomodel.ErrNotFound):
			apiv1.WriteError(w, http.StatusNotFound, "repository not found")
		case errors.Is(err, repomodel.ErrForbidden):
			apiv1.WriteError(w, http.StatusForbidden, "forbidden")
		case errors.Is(err, repomodel.ErrInvalidVisibility):
			apiv1.WriteError(w, http.StatusBadRequest, "visibility must be public or private")
		default:
			slog.Error("visibility update failed", "namespace", namespace, "repository", repositoryName, "err", err)
			apiv1.WriteError(w, http.StatusInternalServerError, "visibility update failed")
		}
		return
	}

	apiv1.WriteJSON(w, http.StatusOK, map[string]bool{"success": true})
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
	return apiv1.RepositoryPath(repositoryParamName, changeVisibilityPathPrefix, "")
}
