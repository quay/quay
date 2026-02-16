package config

import (
	"context"
	"crypto/x509"
	"fmt"
	"time"
)

// Severity indicates whether a validation finding is an error or a warning.
type Severity string

// Severity levels for validation findings.
const (
	SeverityError   Severity = "error"
	SeverityWarning Severity = "warning"
)

// ValidationError represents a single validation finding.
type ValidationError struct {
	Field    string
	Severity Severity
	Message  string
}

func (e ValidationError) String() string {
	return fmt.Sprintf("[%s] %s: %s", e.Severity, e.Field, e.Message)
}

// ProbeResult is the outcome of a single online probe.
type ProbeResult struct {
	Name     string
	Duration time.Duration
	Error    error // nil = success
}

// Probe checks whether a service Quay depends on is reachable.
type Probe interface {
	Name() string
	Check(ctx context.Context, cfg *Config, opts ValidateOptions) ProbeResult
}

// ValidateOptions controls validation behavior.
type ValidateOptions struct {
	// Mode is "offline" (structural checks only) or "online" (connectivity probes).
	Mode string
	// Probes are online connectivity checks injected by the CLI layer.
	Probes []Probe
	// Certificates holds cert/key file contents loaded from the config directory.
	Certificates map[string][]byte
	// CertPool is the TLS certificate pool built from Certificates.
	CertPool *x509.CertPool
}

// Validate runs all validators against cfg and returns any findings.
// Validators are called in a defined order; no init() registration.
// The context is threaded through to online probes for cancellation support.
func Validate(ctx context.Context, cfg *Config, opts ValidateOptions) []ValidationError {
	var errs []ValidationError
	errs = append(errs, validateRequired(cfg, opts)...)
	errs = append(errs, validateServer(cfg, opts)...)
	errs = append(errs, validateDatabase(cfg, opts)...)
	errs = append(errs, validateStorage(cfg, opts)...)
	errs = append(errs, validateRedis(cfg, opts)...)
	errs = append(errs, validateAuth(cfg, opts)...)
	errs = append(errs, validateSecurity(cfg, opts)...)

	// Phase 2: online probes (only if offline passed and mode is "online").
	if opts.Mode == "online" && !HasErrors(errs) {
		errs = append(errs, runProbes(ctx, cfg, opts)...)
	}

	return errs
}

// HasErrors returns true if any finding has error severity.
func HasErrors(errs []ValidationError) bool {
	for _, e := range errs {
		if e.Severity == SeverityError {
			return true
		}
	}
	return false
}

// DefaultProbes returns probes for all configured services. Unconfigured
// services are skipped. No probes are implemented yet.
func DefaultProbes(_ *Config) []Probe {
	return nil
}

// runProbes executes each probe sequentially and converts results to
// ValidationError entries. The parent context is passed to each probe.
func runProbes(ctx context.Context, cfg *Config, opts ValidateOptions) []ValidationError {
	var errs []ValidationError
	for _, p := range opts.Probes {
		result := p.Check(ctx, cfg, opts)
		if result.Error != nil {
			errs = append(errs, ValidationError{
				Field:    result.Name,
				Severity: SeverityError,
				Message:  fmt.Sprintf("probe failed (%.2fs): %v", result.Duration.Seconds(), result.Error),
			})
		}
	}
	return errs
}
