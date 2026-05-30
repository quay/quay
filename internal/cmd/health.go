package cmd

import (
	"context"
	"database/sql"
	"encoding/json"
	"net/http"
	"time"
)

type healthHandler struct {
	db *sql.DB
}

func newHealthHandler(db *sql.DB) *healthHandler {
	return &healthHandler{db: db}
}

func (h *healthHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if h.db != nil {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()

		var result int
		if err := h.db.QueryRowContext(ctx, "SELECT 1").Scan(&result); err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusServiceUnavailable)
			_ = json.NewEncoder(w).Encode(map[string]string{"status": "unhealthy"})
			return
		}
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
