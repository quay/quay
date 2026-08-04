// Package features resolves raw configuration feature flags into immutable
// runtime settings.
package features

import "github.com/quay/quay/internal/config"

// Set contains effective values for features consumed by the Go registry.
//
// Config uses pointer booleans so it can distinguish an omitted YAML value
// from an explicit false. Runtime components should use Set instead, where
// every feature has a concrete value.
type Set struct {
	superUsers           bool
	superUsersFullAccess bool
	anonymousAccess      bool
	referrersAPI         bool
	librarySupport       bool
	userLastAccessed     bool
}

// FromConfig resolves the feature values consumed by the Go registry. Nil
// values use the corresponding Python configuration default.
func FromConfig(cfg config.Features) Set {
	return Set{
		superUsers:           valueOrDefault(cfg.FeatureSuperUsers, config.DefaultFeatureSuperUsers),
		superUsersFullAccess: valueOrDefault(cfg.FeatureSuperUsersFullAccess, config.DefaultFeatureSuperUsersFullAccess),
		anonymousAccess:      valueOrDefault(cfg.FeatureAnonymousAccess, config.DefaultFeatureAnonymousAccess),
		referrersAPI:         valueOrDefault(cfg.FeatureReferrersAPI, config.DefaultFeatureReferrersAPI),
		librarySupport:       valueOrDefault(cfg.FeatureLibrarySupport, config.DefaultFeatureLibrarySupport),
		userLastAccessed:     valueOrDefault(cfg.FeatureUserLastAccessed, config.DefaultFeatureUserLastAccessed),
	}
}

// SuperUsersEnabled reports whether superusers are enabled.
func (s Set) SuperUsersEnabled() bool {
	return s.superUsers
}

// SuperUsersFullAccessEnabled reports whether the full-access superuser flag
// is enabled, independently of whether superusers themselves are enabled.
func (s Set) SuperUsersFullAccessEnabled() bool {
	return s.superUsersFullAccess
}

// HasFullSuperuserAccess reports whether the two superuser flags jointly grant
// full access.
func (s Set) HasFullSuperuserAccess() bool {
	return s.superUsers && s.superUsersFullAccess
}

// AnonymousAccessEnabled reports whether anonymous access is enabled.
func (s Set) AnonymousAccessEnabled() bool {
	return s.anonymousAccess
}

// ReferrersAPIEnabled reports whether the OCI referrers API is enabled.
func (s Set) ReferrersAPIEnabled() bool {
	return s.referrersAPI
}

// LibrarySupportEnabled reports whether namespace-less library repositories
// are supported.
func (s Set) LibrarySupportEnabled() bool {
	return s.librarySupport
}

// UserLastAccessedEnabled reports whether user last-accessed timestamps are
// updated.
func (s Set) UserLastAccessedEnabled() bool {
	return s.userLastAccessed
}

func valueOrDefault(value *bool, defaultValue bool) bool {
	if value == nil {
		return defaultValue
	}
	return *value
}
