package distribution

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestRuntimeCloseRunsCleanupInReverseOrder(t *testing.T) {
	var got []string
	var contextCanceled []bool

	runtime, err := New(t.Context(), func(ctx context.Context, onClose OnClose) (http.Handler, error) {
		onClose(func() error {
			got = append(got, "first")
			contextCanceled = append(contextCanceled, ctx.Err() != nil)
			return nil
		})
		onClose(func() error {
			got = append(got, "second")
			contextCanceled = append(contextCanceled, ctx.Err() != nil)
			return nil
		})
		return http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}), nil
	})
	if err != nil {
		t.Fatalf("New: %v", err)
	}

	if err := runtime.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	if err := runtime.Close(); err != nil {
		t.Fatalf("second Close: %v", err)
	}

	want := []string{"second", "first"}
	if len(got) != len(want) {
		t.Fatalf("cleanup = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("cleanup[%d] = %q, want %q", i, got[i], want[i])
		}
		if !contextCanceled[i] {
			t.Errorf("cleanup[%d] observed an active context", i)
		}
	}
}

func TestNewConvertsPanicAndRollsBackAfterCancel(t *testing.T) {
	var got []string
	var contextCanceled []bool
	var builderContext context.Context

	_, err := New(t.Context(), func(ctx context.Context, onClose OnClose) (http.Handler, error) {
		builderContext = ctx
		onClose(func() error {
			got = append(got, "first")
			contextCanceled = append(contextCanceled, ctx.Err() != nil)
			return nil
		})
		onClose(func() error {
			got = append(got, "second")
			contextCanceled = append(contextCanceled, ctx.Err() != nil)
			return nil
		})
		panic("test panic")
	})
	if err == nil || !strings.Contains(err.Error(), "distribution constructor panicked: test panic") {
		t.Fatalf("New error = %v, want panic conversion", err)
	}
	if got := strings.Join(got, ","); got != "second,first" {
		t.Fatalf("cleanup order = %q, want second,first", got)
	}
	for i, canceled := range contextCanceled {
		if !canceled {
			t.Errorf("cleanup[%d] observed an active context", i)
		}
	}
	select {
	case <-builderContext.Done():
	default:
		t.Fatal("builder context was not canceled after panic rollback")
	}
}

func TestNewBuilderErrorRollsBackAfterCancelAndJoinsErrors(t *testing.T) {
	buildErr := errors.New("build failed")
	cleanupErr := errors.New("cleanup failed")
	var builderContext context.Context

	_, err := New(t.Context(), func(ctx context.Context, onClose OnClose) (http.Handler, error) {
		builderContext = ctx
		onClose(func() error {
			if ctx.Err() == nil {
				t.Error("cleanup observed an active context")
			}
			return cleanupErr
		})
		return nil, buildErr
	})
	if !errors.Is(err, buildErr) || !errors.Is(err, cleanupErr) {
		t.Fatalf("New error = %v, want build and cleanup errors", err)
	}
	select {
	case <-builderContext.Done():
	default:
		t.Fatal("builder context was not canceled after build failure")
	}
}

func TestNewBuilderErrorCleansRegisteredHandlerOnce(t *testing.T) {
	buildErr := errors.New("error after handler setup")
	cleanupCount := 0

	_, err := New(t.Context(), func(_ context.Context, onClose OnClose) (http.Handler, error) {
		onClose(func() error {
			cleanupCount++
			return nil
		})
		return nil, buildErr
	})
	if !errors.Is(err, buildErr) {
		t.Fatalf("New error = %v, want %v", err, buildErr)
	}
	if cleanupCount != 1 {
		t.Fatalf("cleanup count = %d, want 1", cleanupCount)
	}
}

func TestNewRejectsNilContextAndBuilder(t *testing.T) {
	var nilContext context.Context
	if _, err := New(nilContext, func(context.Context, OnClose) (http.Handler, error) {
		return http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}), nil
	}); err == nil { //nolint:staticcheck // intentionally verifies nil-context rejection
		t.Fatal("New(nil context) succeeded")
	}
	if _, err := New(context.Background(), nil); err == nil {
		t.Fatal("New(nil builder) succeeded")
	}
}

func TestNewRejectsNilHandlerAndCleansResources(t *testing.T) {
	cleanupCount := 0
	var nilHandler http.Handler
	_, err := New(t.Context(), func(_ context.Context, onClose OnClose) (http.Handler, error) {
		onClose(func() error {
			cleanupCount++
			return nil
		})
		return nilHandler, nil
	})
	if err == nil || !strings.Contains(err.Error(), "builder returned nil handler") {
		t.Fatalf("New error = %v, want nil handler error", err)
	}
	if cleanupCount != 1 {
		t.Fatalf("cleanup count = %d, want 1", cleanupCount)
	}
}

func TestOnCloseCannotBeUsedAfterBuilderReturns(t *testing.T) {
	var onClose OnClose
	runtime, err := New(t.Context(), func(_ context.Context, register OnClose) (http.Handler, error) {
		onClose = register
		return http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}), nil
	})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	defer func() {
		if recovered := recover(); recovered == nil {
			t.Fatal("late cleanup registration did not panic")
		}
		if err := runtime.Close(); err != nil {
			t.Fatalf("Close after late registration panic: %v", err)
		}
	}()
	onClose(func() error { return nil })
}

func TestRuntimeHandlerCloseAndCloseErrors(t *testing.T) {
	shutdownErr := errors.New("shutdown failed")
	cleanupErr := errors.New("cleanup failed")
	var handlerCalled bool
	handler := http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		handlerCalled = true
	})

	runtime, err := New(t.Context(), func(_ context.Context, onClose OnClose) (http.Handler, error) {
		onClose(func() error { return cleanupErr })
		return handler, nil
	})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	runtime.Handler().ServeHTTP(httptest.NewRecorder(), httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody))
	if !handlerCalled {
		t.Fatal("Runtime.Handler did not dispatch to the built handler")
	}

	// A shutdown callback is just another cleanup registered by the builder.
	runtime2, err := New(t.Context(), func(_ context.Context, onClose OnClose) (http.Handler, error) {
		onClose(func() error { return shutdownErr })
		onClose(func() error { return cleanupErr })
		return handler, nil
	})
	if err != nil {
		t.Fatalf("second New: %v", err)
	}
	closeErr := runtime2.Close()
	if !errors.Is(closeErr, shutdownErr) || !errors.Is(closeErr, cleanupErr) {
		t.Fatalf("Close error = %v, want both cleanup errors", closeErr)
	}
	if err := runtime2.Close(); !errors.Is(err, shutdownErr) || !errors.Is(err, cleanupErr) {
		t.Fatalf("second Close error = %v, want the same errors", err)
	}
	if err := runtime.Close(); !errors.Is(err, cleanupErr) {
		t.Fatalf("first Close error = %v, want cleanup error", err)
	}

	var nilRuntime *Runtime
	if nilRuntime.Handler() != nil {
		t.Fatal("nil Runtime.Handler returned a handler")
	}
	if err := nilRuntime.Close(); err != nil {
		t.Fatalf("nil Runtime.Close: %v", err)
	}
}
