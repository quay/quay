package repository

import (
	"context"

	"github.com/quay/quay/internal/auth"
)

// OwnerOrBootstrapAdminAuthorizer grants repository admin to the namespace
// owner and the standalone registry bootstrap admin.
//
// Full Quay permission-table authorization can replace this implementation
// without changing repository service callers.
type OwnerOrBootstrapAdminAuthorizer struct {
	AdminUsername string
}

// CanAdminRepository reports whether actor can administer repo.
func (a OwnerOrBootstrapAdminAuthorizer) CanAdminRepository(_ context.Context, principal *auth.Principal, repo Repository) (bool, error) {
	if principal.IsAnonymous() {
		return false, nil
	}
	return principal.Username == repo.Ref.Namespace ||
		(a.AdminUsername != "" && principal.Username == a.AdminUsername), nil
}
