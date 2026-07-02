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
)

// Valid reports whether v is a supported repository visibility.
func (v Visibility) Valid() bool {
	return v == VisibilityPublic || v == VisibilityPrivate
}

// Repository contains repository fields needed by business operations.
type Repository struct {
	ID         int64
	Ref        Ref
	Visibility Visibility
}
