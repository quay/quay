package oci

import (
	"context"
	"sync"

	"github.com/opencontainers/go-digest"
)

// BlobLocker serializes filesystem and metadata changes for one blob digest.
type BlobLocker interface {
	Lock(ctx context.Context, dgst digest.Digest) (unlock func(), err error)
}

// BlobLockSet coordinates blob operations within one process. Deployments with
// multiple processes sharing one storage directory need cross-process locking.
type BlobLockSet struct {
	mu    sync.Mutex
	locks map[digest.Digest]*blobLock
}

type blobLock struct {
	semaphore  chan struct{}
	references int
}

// NewBlobLockSet creates an empty set of per-digest locks.
func NewBlobLockSet() *BlobLockSet {
	return &BlobLockSet{locks: make(map[digest.Digest]*blobLock)}
}

// Lock acquires the lock for dgst or returns when ctx is canceled. The returned
// unlock function is safe to call more than once.
func (s *BlobLockSet) Lock(ctx context.Context, dgst digest.Digest) (func(), error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	s.mu.Lock()
	if s.locks == nil {
		s.locks = make(map[digest.Digest]*blobLock)
	}
	entry := s.locks[dgst]
	if entry == nil {
		entry = &blobLock{semaphore: make(chan struct{}, 1)}
		entry.semaphore <- struct{}{}
		s.locks[dgst] = entry
	}
	entry.references++
	s.mu.Unlock()

	select {
	case <-ctx.Done():
		s.removeReference(dgst, entry)
		return nil, ctx.Err()
	case <-entry.semaphore:
	}

	var once sync.Once
	return func() {
		once.Do(func() {
			s.mu.Lock()
			defer s.mu.Unlock()

			entry.references--
			if entry.references == 0 {
				delete(s.locks, dgst)
				return
			}
			entry.semaphore <- struct{}{}
		})
	}, nil
}

func (s *BlobLockSet) removeReference(dgst digest.Digest, entry *blobLock) {
	s.mu.Lock()
	defer s.mu.Unlock()

	entry.references--
	if entry.references == 0 {
		delete(s.locks, dgst)
	}
}
