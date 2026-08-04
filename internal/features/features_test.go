package features

import (
	"testing"

	"github.com/quay/quay/internal/config"
	"github.com/stretchr/testify/assert"
)

func TestFromConfigUsesPythonDefaultsForUnsetFeatures(t *testing.T) {
	got := FromConfig(config.Features{})

	assert.True(t, got.SuperUsersEnabled())
	assert.False(t, got.SuperUsersFullAccessEnabled())
	assert.True(t, got.AnonymousAccessEnabled())
	assert.True(t, got.ReferrersAPIEnabled())
	assert.True(t, got.LibrarySupportEnabled())
	assert.True(t, got.UserLastAccessedEnabled())
	assert.False(t, got.HasFullSuperuserAccess())
}

func TestFromConfigPreservesStandaloneSuperuserSettings(t *testing.T) {
	got := FromConfig(config.NewDefault("localhost", "/data/storage").Features)

	assert.True(t, got.SuperUsersEnabled())
	assert.True(t, got.SuperUsersFullAccessEnabled())
	assert.True(t, got.HasFullSuperuserAccess())
}

func TestFromConfigPreservesExplicitValues(t *testing.T) {
	falseValue := false
	trueValue := true
	got := FromConfig(config.Features{
		FeatureSuperUsers:           &falseValue,
		FeatureSuperUsersFullAccess: &trueValue,
		FeatureAnonymousAccess:      &falseValue,
		FeatureReferrersAPI:         &falseValue,
		FeatureLibrarySupport:       &falseValue,
		FeatureUserLastAccessed:     &falseValue,
	})

	assert.False(t, got.SuperUsersEnabled())
	assert.True(t, got.SuperUsersFullAccessEnabled())
	assert.False(t, got.AnonymousAccessEnabled())
	assert.False(t, got.ReferrersAPIEnabled())
	assert.False(t, got.LibrarySupportEnabled())
	assert.False(t, got.UserLastAccessedEnabled())
	assert.False(t, got.HasFullSuperuserAccess())
}

func TestHasFullSuperuserAccessRequiresBothFlags(t *testing.T) {
	for _, test := range []struct {
		name               string
		superUsers         bool
		fullAccess         bool
		expectedFullAccess bool
	}{
		{name: "both disabled", superUsers: false, fullAccess: false, expectedFullAccess: false},
		{name: "superusers only", superUsers: true, fullAccess: false, expectedFullAccess: false},
		{name: "full access only", superUsers: false, fullAccess: true, expectedFullAccess: false},
		{name: "both enabled", superUsers: true, fullAccess: true, expectedFullAccess: true},
	} {
		t.Run(test.name, func(t *testing.T) {
			superUsers := test.superUsers
			fullAccess := test.fullAccess
			got := FromConfig(config.Features{
				FeatureSuperUsers:           &superUsers,
				FeatureSuperUsersFullAccess: &fullAccess,
			})

			assert.Equal(t, test.expectedFullAccess, got.HasFullSuperuserAccess())
		})
	}
}
