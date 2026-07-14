package distribution

import (
	"strings"
	"testing"
)

func TestNewRegistryRejectsNilBlobLocker(t *testing.T) {
	_, err := NewRegistry(t.Context(), &Config{})
	if err == nil {
		t.Fatal("expected missing blob locker to be rejected")
	}
	if !strings.Contains(err.Error(), "nil blob locker") {
		t.Fatalf("expected nil blob locker error, got %v", err)
	}
}
