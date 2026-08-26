package oci

import (
	"context"
	"testing"
	"time"

	"github.com/opencontainers/go-digest"
	"github.com/stretchr/testify/require"
)

func TestBlobLockSetSerializesSameDigest(t *testing.T) {
	locks := NewBlobLockSet()
	dgst := digest.FromString("same")

	unlockFirst, err := locks.Lock(t.Context(), dgst)
	require.NoError(t, err)

	acquired := make(chan func(), 1)
	go func() {
		unlock, lockErr := locks.Lock(t.Context(), dgst)
		if lockErr == nil {
			acquired <- unlock
		}
	}()

	require.Eventually(t, func() bool {
		return blobLockReferenceCount(locks, dgst) == 2
	}, time.Second, time.Millisecond)
	select {
	case <-acquired:
		t.Fatal("second same-digest lock acquired before the first was released")
	default:
	}

	unlockFirst()
	select {
	case unlockSecond := <-acquired:
		unlockSecond()
	case <-time.After(time.Second):
		t.Fatal("second same-digest lock did not acquire after release")
	}
	requireBlobLockSetEmpty(t, locks)
}

func TestBlobLockSetAllowsDifferentDigests(t *testing.T) {
	locks := NewBlobLockSet()
	unlockFirst, err := locks.Lock(t.Context(), digest.FromString("first"))
	require.NoError(t, err)

	acquired := make(chan func(), 1)
	go func() {
		unlock, lockErr := locks.Lock(t.Context(), digest.FromString("second"))
		if lockErr == nil {
			acquired <- unlock
		}
	}()

	select {
	case unlockSecond := <-acquired:
		unlockSecond()
	case <-time.After(time.Second):
		t.Fatal("different digest was blocked")
	}
	unlockFirst()
	requireBlobLockSetEmpty(t, locks)
}

func TestBlobLockSetCanceledWaiterIsRemoved(t *testing.T) {
	locks := NewBlobLockSet()
	dgst := digest.FromString("canceled")
	unlock, err := locks.Lock(t.Context(), dgst)
	require.NoError(t, err)

	ctx, cancel := context.WithCancel(t.Context())
	waiterDone := make(chan error, 1)
	go func() {
		_, lockErr := locks.Lock(ctx, dgst)
		waiterDone <- lockErr
	}()
	require.Eventually(t, func() bool {
		return blobLockReferenceCount(locks, dgst) == 2
	}, time.Second, time.Millisecond)

	cancel()
	require.ErrorIs(t, <-waiterDone, context.Canceled)
	require.Equal(t, 1, blobLockReferenceCount(locks, dgst))

	unlock()
	requireBlobLockSetEmpty(t, locks)
}

func TestBlobLockSetUnlockIsIdempotent(t *testing.T) {
	locks := NewBlobLockSet()
	dgst := digest.FromString("idempotent")

	unlock, err := locks.Lock(t.Context(), dgst)
	require.NoError(t, err)
	unlock()
	unlock()
	requireBlobLockSetEmpty(t, locks)

	unlockAgain, err := locks.Lock(t.Context(), dgst)
	require.NoError(t, err)
	unlockAgain()
	requireBlobLockSetEmpty(t, locks)
}

func blobLockReferenceCount(locks *BlobLockSet, dgst digest.Digest) int {
	locks.mu.Lock()
	defer locks.mu.Unlock()
	if entry := locks.locks[dgst]; entry != nil {
		return entry.references
	}
	return 0
}

func requireBlobLockSetEmpty(t *testing.T, locks *BlobLockSet) {
	t.Helper()
	locks.mu.Lock()
	defer locks.mu.Unlock()
	require.Empty(t, locks.locks)
}
