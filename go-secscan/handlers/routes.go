package handlers

import (
	"net/http"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/goccy/go-json"

	"github.com/quay/go-secscan/config"
	"github.com/quay/go-secscan/models"
)

// Routes registers Clair v4-compatible endpoints
func Routes(cfg config.Config, store models.Store) chi.Router {
	r := chi.NewRouter()

	r.Get("/indexer/api/v1/index_state", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"state": cfg.IndexerState})
	})

	r.Post("/indexer/api/v1/index_report", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			Hash   string `json:"hash"`
			Layers []struct {
				Hash    string              `json:"hash"`
				URI     string              `json:"uri"`
				Headers map[string][]string `json:"headers"`
			} `json:"layers"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Hash == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"code": "bad-request", "message": "failed to deserialize manifest"})
			return
		}
		store.SaveIndexReport(models.IndexReport{ManifestHash: body.Hash, State: "IndexFinished", Err: ""})
		w.Header().Set("ETag", "\""+cfg.IndexerState+"\"")
		writeJSON(w, http.StatusOK, map[string]any{
			"manifest_hash": body.Hash,
			"state":         "IndexFinished",
			"packages":      map[string]any{},
			"distributions": map[string]any{},
			"repository":    map[string]any{},
			"environments":  map[string]any{},
			"success":       true,
			"err":           "",
		})
	})

	r.Get("/indexer/api/v1/index_report/{hash}", func(w http.ResponseWriter, r *http.Request) {
		h := chi.URLParam(r, "hash")
		if rep, ok := store.GetIndexReport(h); ok {
			writeJSON(w, http.StatusOK, rep)
			return
		}
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "not found"})
	})

	r.Get("/matcher/api/v1/vulnerability_report/{hash}", func(w http.ResponseWriter, r *http.Request) {
		h := chi.URLParam(r, "hash")
		if rep, ok := store.GetVulnReport(h); ok {
			writeJSON(w, http.StatusOK, rep)
			return
		}
		// Minimal empty report to match client expectations
		writeJSON(w, http.StatusOK, models.VulnerabilityReport{
			ManifestHash:           h,
			Packages:               map[string]models.Package{},
			Environments:           map[string][]models.Environment{},
			Vulnerabilities:        map[string]models.Vulnerability{},
			PackageVulnerabilities: map[string][]string{},
		})
	})

	r.Get("/notifier/api/v1/notification/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := chi.URLParam(r, "id")
		next := r.URL.Query().Get("next")
		if page, ok := store.GetNotificationPage(id, next, cfg.NotificationPageSize); ok {
			writeJSON(w, http.StatusOK, page)
			return
		}
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "not found"})
	})

	r.Delete("/notifier/api/v1/notification/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := chi.URLParam(r, "id")
		store.DeleteNotification(id)
		w.WriteHeader(http.StatusNoContent)
	})

	r.Delete("/indexer/api/v1/index_report/{hash}", func(w http.ResponseWriter, r *http.Request) {
		h := chi.URLParam(r, "hash")
		store.DeleteIndexReport(h)
		w.WriteHeader(http.StatusNoContent)
	})

	return r
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func getBearer(tokenHeader string) string {
	parts := strings.SplitN(tokenHeader, " ", 2)
	if len(parts) != 2 {
		return ""
	}
	if !strings.EqualFold(parts[0], "Bearer") {
		return ""
	}
	return parts[1]
}
