// Package repository contains repository business operations.
package repository

// Ref identifies a repository by namespace and name.
type Ref struct {
	Namespace string
	Name      string
}

// Visibility is a repository visibility value.
type Visibility string

const (
	// VisibilityPublic makes a repository pullable by anonymous users when enabled.
	VisibilityPublic Visibility = "public"
	// VisibilityPrivate requires authentication and permission to pull.
	VisibilityPrivate Visibility = "private"

	// StateNormal allows repository writes.
	StateNormal int64 = 0
	// StateReadOnly denies repository writes.
	StateReadOnly int64 = 1
	// StateMirror allows writes only from the configured repository mirror robot.
	StateMirror int64 = 2
	// StateMarkedForDeletion hides repositories from normal operations.
	StateMarkedForDeletion int64 = 3
	// StateOrgMirror allows writes only from the configured organization mirror robot.
	StateOrgMirror int64 = 4

	// KindImage is the repositorykind id for image repositories.
	KindImage int64 = 1
)

// Valid reports whether v is a supported repository visibility.
func (v Visibility) Valid() bool {
	return v == VisibilityPublic || v == VisibilityPrivate
}

// Repository contains repository fields needed by business operations.
type Repository struct {
	ID               int64
	Ref              Ref
	Visibility       Visibility
	State            int64
	KindID           int64
	NamespaceEnabled bool
}
