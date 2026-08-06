// Package distribution provides the product-neutral lifecycle runtime used to
// compose HTTP applications around Distribution.
package distribution

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"sync"
)

// Cleanup releases one resource acquired during construction.
type Cleanup func() error

// OnClose registers cleanup synchronously during Builder execution. The
// runtime runs registered cleanups in reverse order on construction failure or
// when Runtime.Close is called.
type OnClose func(Cleanup)

// Builder constructs an application and registers cleanup for resources it
// acquires indirectly through factories. OnClose belongs to the synchronous
// builder call and must not be retained after it returns.
type Builder func(context.Context, OnClose) (http.Handler, error)

type cleanupStack struct {
	cleanups []Cleanup
	sealed   bool
}

func (s *cleanupStack) add(cleanup Cleanup) {
	if cleanup == nil {
		return
	}
	if s.sealed {
		panic("distribution cleanup registered after builder completed")
	}
	s.cleanups = append(s.cleanups, cleanup)
}

func (s *cleanupStack) seal() { s.sealed = true }

func (s *cleanupStack) release() error {
	cleanups := s.cleanups
	s.cleanups = nil
	s.sealed = true

	var cleanupErr error
	for i := len(cleanups) - 1; i >= 0; i-- {
		cleanupErr = errors.Join(cleanupErr, cleanups[i]())
	}
	return cleanupErr
}

// Runtime owns a composed application's handler and lifecycle.
type Runtime struct {
	handler http.Handler
	cancel  context.CancelFunc
	cleanup *cleanupStack

	closeOnce sync.Once
	closeErr  error
}

// New constructs a Runtime. A nil context or builder is rejected. Panics
// raised by the builder are converted into errors after the builder context is
// canceled and registered cleanups are rolled back.
func New(ctx context.Context, build Builder) (runtime *Runtime, err error) {
	if ctx == nil {
		return nil, fmt.Errorf("nil context")
	}
	if build == nil {
		return nil, fmt.Errorf("nil builder")
	}

	stack := &cleanupStack{}
	appCtx, cancel := context.WithCancel(ctx)
	defer func() {
		if recovered := recover(); recovered != nil {
			runtime = nil
			stack.seal()
			cancel()
			cleanupErr := stack.release()
			err = errors.Join(fmt.Errorf("distribution constructor panicked: %v", recovered), cleanupErr)
		}
	}()

	handler, buildErr := build(appCtx, stack.add)
	stack.seal()
	if buildErr != nil {
		return nil, errors.Join(buildErr, rollback(cancel, stack))
	}
	if handler == nil {
		return nil, errors.Join(fmt.Errorf("builder returned nil handler"), rollback(cancel, stack))
	}

	return &Runtime{
		handler: handler,
		cancel:  cancel,
		cleanup: stack,
	}, nil
}

func rollback(cancel context.CancelFunc, stack *cleanupStack) error {
	cancel()
	return stack.release()
}

// Handler returns the application's top-level HTTP handler.
func (r *Runtime) Handler() http.Handler {
	if r == nil {
		return nil
	}
	return r.handler
}

// Close cancels the runtime context and releases all registered resources in
// reverse order. It is idempotent and nil-safe.
func (r *Runtime) Close() error {
	if r == nil {
		return nil
	}
	r.closeOnce.Do(func() {
		if r.cancel != nil {
			r.cancel()
		}
		if r.cleanup != nil {
			r.closeErr = errors.Join(r.closeErr, r.cleanup.release())
		}
	})
	return r.closeErr
}
