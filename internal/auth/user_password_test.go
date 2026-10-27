package auth

import (
	"database/sql"
	"sync/atomic"
	"testing"
	"time"

	"golang.org/x/crypto/bcrypt"
)

// countingVerifier wraps a userPasswordVerifier so tests can count bcrypt
// comparisons and control the cache clock.
type countingVerifier struct {
	*userPasswordVerifier
	db       *sql.DB
	compares atomic.Int32
	clock    time.Time
}

func newCountingVerifier(t *testing.T, ttl time.Duration) *countingVerifier {
	t.Helper()
	db := setupAuthTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	base, ok := NewUserPasswordVerifierWithCacheTTL(db, ttl).(*userPasswordVerifier)
	if !ok {
		t.Fatal("unexpected verifier type")
	}
	cv := &countingVerifier{userPasswordVerifier: base, db: db, clock: time.Date(2026, 9, 11, 12, 0, 0, 0, time.UTC)}
	base.compare = func(hash, password []byte) error {
		cv.compares.Add(1)
		return bcrypt.CompareHashAndPassword(hash, password)
	}
	if base.cache != nil {
		base.cache.now = func() time.Time { return cv.clock }
	}
	return cv
}

func (cv *countingVerifier) verify(t *testing.T, username, secret string) Result {
	t.Helper()
	return cv.Verify(t.Context(), Credentials{Username: username, Secret: secret})
}

func (cv *countingVerifier) expectCompares(t *testing.T, want int32) {
	t.Helper()
	if got := cv.compares.Load(); got != want {
		t.Fatalf("bcrypt comparisons: got %d, want %d", got, want)
	}
}

func TestUserPasswordVerifier_RepeatLoginSkipsBcrypt(t *testing.T) {
	cv := newCountingVerifier(t, DefaultPasswordCacheTTL)

	first := cv.verify(t, "admin", "correct-password")
	if !first.Authenticated {
		t.Fatal("first verification should succeed")
	}
	cv.expectCompares(t, 1)

	for i := 0; i < 5; i++ {
		again := cv.verify(t, "admin", "correct-password")
		if !again.Authenticated {
			t.Fatalf("repeat verification %d should succeed", i)
		}
		if again.Principal != first.Principal {
			t.Fatalf("cached principal %+v differs from %+v", again.Principal, first.Principal)
		}
	}
	cv.expectCompares(t, 1)
}

func TestUserPasswordVerifier_WrongPasswordAlwaysPaysBcrypt(t *testing.T) {
	cv := newCountingVerifier(t, DefaultPasswordCacheTTL)

	for i := 0; i < 3; i++ {
		if cv.verify(t, "admin", "wrong-password").Authenticated {
			t.Fatal("wrong password must not authenticate")
		}
	}
	cv.expectCompares(t, 3)

	// A correct login does not make the wrong one cheap either.
	if !cv.verify(t, "admin", "correct-password").Authenticated {
		t.Fatal("correct password should authenticate")
	}
	if cv.verify(t, "admin", "wrong-password").Authenticated {
		t.Fatal("wrong password must not authenticate after a cached success")
	}
	cv.expectCompares(t, 5)
}

func TestUserPasswordVerifier_PasswordChangeInvalidatesCache(t *testing.T) {
	cv := newCountingVerifier(t, DefaultPasswordCacheTTL)

	if !cv.verify(t, "admin", "correct-password").Authenticated {
		t.Fatal("initial verification should succeed")
	}
	cv.expectCompares(t, 1)

	newHash, err := bcrypt.GenerateFromPassword([]byte("new-password"), bcrypt.MinCost)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := cv.db.ExecContext(t.Context(), `UPDATE "user" SET password_hash = ? WHERE username = 'admin'`, string(newHash)); err != nil {
		t.Fatal(err)
	}

	if cv.verify(t, "admin", "correct-password").Authenticated {
		t.Fatal("old password must be rejected after a password change")
	}
	cv.expectCompares(t, 2)
	if !cv.verify(t, "admin", "new-password").Authenticated {
		t.Fatal("new password should authenticate")
	}
	cv.expectCompares(t, 3)
	if !cv.verify(t, "admin", "new-password").Authenticated {
		t.Fatal("new password should authenticate from cache")
	}
	cv.expectCompares(t, 3)
}

func TestUserPasswordVerifier_DisabledUserRejectedDespiteCache(t *testing.T) {
	cv := newCountingVerifier(t, DefaultPasswordCacheTTL)

	if !cv.verify(t, "admin", "correct-password").Authenticated {
		t.Fatal("initial verification should succeed")
	}
	if _, err := cv.db.ExecContext(t.Context(), `UPDATE "user" SET enabled = 0 WHERE username = 'admin'`); err != nil {
		t.Fatal(err)
	}
	if cv.verify(t, "admin", "correct-password").Authenticated {
		t.Fatal("disabled user must not authenticate from cache")
	}
}

func TestUserPasswordVerifier_CacheEntryExpires(t *testing.T) {
	cv := newCountingVerifier(t, time.Minute)

	cv.verify(t, "admin", "correct-password")
	cv.clock = cv.clock.Add(59 * time.Second)
	cv.verify(t, "admin", "correct-password")
	cv.expectCompares(t, 1)

	cv.clock = cv.clock.Add(2 * time.Second)
	if !cv.verify(t, "admin", "correct-password").Authenticated {
		t.Fatal("verification after expiry should still succeed")
	}
	cv.expectCompares(t, 2)
	cv.verify(t, "admin", "correct-password")
	cv.expectCompares(t, 2)
}

func TestUserPasswordVerifier_CacheDisabled(t *testing.T) {
	cv := newCountingVerifier(t, 0)
	if cv.cache != nil {
		t.Fatal("ttl 0 must disable the cache")
	}
	for i := 0; i < 3; i++ {
		if !cv.verify(t, "admin", "correct-password").Authenticated {
			t.Fatal("verification should succeed")
		}
	}
	cv.expectCompares(t, 3)
}

func TestUserPasswordVerifier_UnknownUserStillRunsComparison(t *testing.T) {
	cv := newCountingVerifier(t, DefaultPasswordCacheTTL)
	for i := 0; i < 2; i++ {
		if cv.verify(t, "nobody", "anything").Authenticated {
			t.Fatal("unknown user must not authenticate")
		}
	}
	// The dummy comparison keeps timing independent of whether the user exists.
	cv.expectCompares(t, 2)
}

func TestCredentialCache_SecretIsNotStoredAndUserIsIsolated(t *testing.T) {
	cache := newCredentialCache(time.Minute)
	if cache == nil {
		t.Fatal("cache should be enabled")
	}
	cache.remember("alice", "$hash-a", "alice-secret")
	if !cache.matches("alice", "$hash-a", "alice-secret") {
		t.Fatal("expected a hit for the remembered credentials")
	}
	if cache.matches("alice", "$hash-a", "bob-secret") {
		t.Fatal("different secret must miss")
	}
	if cache.matches("alice", "$hash-b", "alice-secret") {
		t.Fatal("different stored hash must miss")
	}
	if cache.matches("bob", "$hash-a", "alice-secret") {
		t.Fatal("different username must miss")
	}
	for _, entry := range cache.entries {
		if string(entry.secretMAC) == "alice-secret" {
			t.Fatal("cache must not hold the plaintext secret")
		}
	}
}

func TestCredentialCache_Bounded(t *testing.T) {
	cache := newCredentialCache(time.Minute)
	base := time.Date(2026, 9, 11, 12, 0, 0, 0, time.UTC)
	tick := 0
	cache.now = func() time.Time { tick++; return base.Add(time.Duration(tick) * time.Millisecond) }
	for i := 0; i < maxCredentialCacheEntries+10; i++ {
		cache.remember(string(rune('a'+i%26))+"-"+time.Duration(i).String(), "$h", "s")
	}
	if got := len(cache.entries); got > maxCredentialCacheEntries {
		t.Fatalf("cache grew to %d entries, want at most %d", got, maxCredentialCacheEntries)
	}
}
