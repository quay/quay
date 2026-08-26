package middleware

import (
	"context"
	"net/http"

	"github.com/opencontainers/go-digest"
)

type contextKey struct{}

// subjectHolder is a mutable container placed into the request context
// before distribution handles the request. The middleware writes into it;
// the HTTP wrapper reads from it after the response status is known.
type subjectHolder struct {
	digest digest.Digest
}

// WithSubjectHolder returns a context that carries an empty subjectHolder.
// Call this before handing the request to distribution.
func WithSubjectHolder(ctx context.Context) context.Context {
	return context.WithValue(ctx, contextKey{}, &subjectHolder{})
}

// SetSubject stores a subject digest into the holder in ctx.
// Called by the manifest middleware after a successful Put.
func SetSubject(ctx context.Context, d digest.Digest) {
	if h, ok := ctx.Value(contextKey{}).(*subjectHolder); ok {
		h.digest = d
	}
}

// subjectFromContext retrieves the subject digest from the holder in ctx.
func subjectFromContext(ctx context.Context) (digest.Digest, bool) {
	h, ok := ctx.Value(contextKey{}).(*subjectHolder)
	if !ok || h.digest == "" {
		return "", false
	}
	return h.digest, true
}

// SubjectHeaderMiddleware wraps an http.Handler and sets the OCI-Subject
// response header on successful manifest PUT responses when the pushed
// manifest contained a subject field.
func SubjectHeaderMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut {
			next.ServeHTTP(w, r)
			return
		}
		r = r.WithContext(WithSubjectHolder(r.Context()))
		sw := &subjectWriter{ResponseWriter: w, req: r}
		next.ServeHTTP(sw, r)
	})
}

type subjectWriter struct {
	http.ResponseWriter
	req         *http.Request
	wroteHeader bool
}

func (sw *subjectWriter) WriteHeader(code int) {
	if !sw.wroteHeader {
		sw.wroteHeader = true
		if code >= 200 && code < 300 {
			if d, ok := subjectFromContext(sw.req.Context()); ok {
				sw.ResponseWriter.Header().Set("OCI-Subject", d.String())
			}
		}
	}
	sw.ResponseWriter.WriteHeader(code)
}

func (sw *subjectWriter) Write(b []byte) (int, error) {
	if !sw.wroteHeader {
		sw.WriteHeader(http.StatusOK)
	}
	return sw.ResponseWriter.Write(b)
}
