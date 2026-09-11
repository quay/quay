package auth

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"sync"
	"time"
)

// DefaultPasswordCacheTTL is how long a successful password verification is
// remembered so repeat logins with the same credentials skip bcrypt.
const DefaultPasswordCacheTTL = 5 * time.Minute

// maxCredentialCacheEntries bounds the cache; the mirror registry has a
// handful of users, so this is far above any realistic working set.
const maxCredentialCacheEntries = 1024

// credentialCache remembers recent successful password verifications.
//
// A bcrypt comparison at the cost factor Quay uses takes roughly a third of a
// CPU second on a small host, and registry clients request a new token for
// every image (skopeo asks twice per push), so on a single-process mirror
// registry token issuance was the dominant CPU cost of a push. Quay's Python
// service has the same per-login cost but is rarely hit by it because
// production clients use robot accounts, whose secret is compared without
// bcrypt.
//
// The cache never stores the secret itself: it keeps an HMAC-SHA256 of the
// presented secret under a random per-process key, together with the password
// hash that was current when the verification succeeded. A hit requires the
// same username, an unexpired entry, the same stored hash (so a password
// change invalidates immediately) and a matching HMAC. Only successful
// verifications are cached, so a wrong password always pays the full bcrypt
// cost and gains no timing information.
type credentialCache struct {
	ttl time.Duration
	now func() time.Time
	key []byte

	mu      sync.Mutex
	entries map[string]credentialCacheEntry
}

type credentialCacheEntry struct {
	passwordHash string
	secretMAC    []byte
	expiresAt    time.Time
}

func newCredentialCache(ttl time.Duration) *credentialCache {
	if ttl <= 0 {
		return nil
	}
	key := make([]byte, sha256.Size)
	if _, err := rand.Read(key); err != nil {
		// Without a random key the cache cannot be made safe; run without it.
		return nil
	}
	return &credentialCache{
		ttl:     ttl,
		now:     time.Now,
		key:     key,
		entries: make(map[string]credentialCacheEntry),
	}
}

func (c *credentialCache) mac(secret string) []byte {
	h := hmac.New(sha256.New, c.key)
	h.Write([]byte(secret))
	return h.Sum(nil)
}

// matches reports whether a recent successful verification exists for the
// same username, stored password hash and secret.
func (c *credentialCache) matches(username, passwordHash, secret string) bool {
	if c == nil {
		return false
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	entry, ok := c.entries[username]
	if !ok {
		return false
	}
	if !c.now().Before(entry.expiresAt) {
		delete(c.entries, username)
		return false
	}
	if subtle.ConstantTimeCompare([]byte(entry.passwordHash), []byte(passwordHash)) != 1 {
		delete(c.entries, username)
		return false
	}
	return hmac.Equal(entry.secretMAC, c.mac(secret))
}

// remember records a successful verification.
func (c *credentialCache) remember(username, passwordHash, secret string) {
	if c == nil {
		return
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	now := c.now()
	if len(c.entries) >= maxCredentialCacheEntries {
		c.evictLocked(now)
	}
	c.entries[username] = credentialCacheEntry{
		passwordHash: passwordHash,
		secretMAC:    c.mac(secret),
		expiresAt:    now.Add(c.ttl),
	}
}

// evictLocked drops expired entries and, if the cache is still full, the
// entry closest to expiry.
func (c *credentialCache) evictLocked(now time.Time) {
	var oldestKey string
	var oldest time.Time
	for key, entry := range c.entries {
		if !now.Before(entry.expiresAt) {
			delete(c.entries, key)
			continue
		}
		if oldestKey == "" || entry.expiresAt.Before(oldest) {
			oldestKey, oldest = key, entry.expiresAt
		}
	}
	if len(c.entries) >= maxCredentialCacheEntries && oldestKey != "" {
		delete(c.entries, oldestKey)
	}
}
