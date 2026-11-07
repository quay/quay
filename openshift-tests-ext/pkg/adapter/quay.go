package adapter

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"sync"
	"syscall"
	"time"

	ext "github.com/openshift-eng/openshift-tests-extension/pkg/extension/extensiontests"
	"github.com/openshift-eng/openshift-tests-extension/pkg/util/sets"
)

const (
	// quayDefaultTimeout is the default timeout for Quay tests.
	quayDefaultTimeoutStr = "5m"
	quayDefaultTimeout    = 5 * time.Minute

	// quayShutdownGracePeriod is how long we wait after SIGTERM before SIGKILL.
	quayShutdownGracePeriod = 10 * time.Second

	// maxCapturedOutputBytes bounds captured stdout+stderr.
	maxCapturedOutputBytes = 512 * 1024
)

// BuildExtensionTestSpecsFromQuayScenarios parses a JSON array of ScenarioSpec
// entries and produces one ExtensionTestSpec per entry.
//
// Usage in a binary:
//
//	specs, err := adapter.BuildExtensionTestSpecsFromQuayScenarios(scenarioMetadata, nil)
func BuildExtensionTestSpecsFromQuayScenarios(metadata []byte, scriptFS fs.FS) (ext.ExtensionTestSpecs, error) {
	var scenarios []ScenarioSpec
	if err := json.Unmarshal(metadata, &scenarios); err != nil {
		return nil, fmt.Errorf("failed to unmarshal Quay scenario metadata: %w", err)
	}

	specs := make(ext.ExtensionTestSpecs, 0, len(scenarios))
	for _, sc := range scenarios {
		sc := sc // capture loop variable

		if err := validateScenarioSpec(sc); err != nil {
			return nil, err
		}

		lifecycle := ext.LifecycleBlocking
		if sc.Informing {
			lifecycle = ext.LifecycleInforming
		}

		spec := &ext.ExtensionTestSpec{
			Name:          sc.Name,
			Labels:        sets.New(sc.Tags...),
			CodeLocations: []string{codeLocation(sc)},
			Lifecycle:     lifecycle,
			Resources: ext.Resources{
				Timeout: resolveTimeoutStr(sc.Timeout),
			},
			EnvironmentSelector: ext.EnvironmentSelector{
				Include: sc.IncludeCEL,
				Exclude: sc.ExcludeCEL,
			},
			Timeout: resolveTimeout(sc.Timeout, quayDefaultTimeout),
		}

		// Add tags as metadata
		spec.Tags = make(map[string]string)
		for _, tag := range sc.Tags {
			spec.Tags[tag] = "true"
		}
		spec.Tags["component"] = getComponent(sc.Tags)

		runFn := func(ctx context.Context) *ext.ExtensionTestResult {
			timeout := spec.Timeout
			if timeout <= 0 {
				timeout = quayDefaultTimeout
			}
			return runQuayScenario(ctx, sc, scriptFS, timeout)
		}
		spec.Run = runFn
		spec.RunParallel = runFn

		specs = append(specs, spec)
	}

	return specs, nil
}

// validateScenarioSpec checks that the scenario has required fields populated.
func validateScenarioSpec(sc ScenarioSpec) error {
	if sc.Name == "" {
		return fmt.Errorf("scenario spec is missing name")
	}
	if sc.Entrypoint == "" {
		return fmt.Errorf("scenario %q must set entrypoint", sc.Name)
	}
	return nil
}

// codeLocation builds a code location string from the scenario's workdir and entrypoint.
func codeLocation(sc ScenarioSpec) string {
	if sc.Entrypoint != "" {
		if sc.WorkDir != "" {
			return sc.WorkDir + " " + sc.Entrypoint
		}
		return sc.Entrypoint
	}
	return ""
}

// getComponent extracts the component name from scenario tags, defaulting to "quay".
func getComponent(tags []string) string {
	// Extract component from tags
	for _, tag := range tags {
		if tag == "quay" {
			return "quay"
		}
	}
	return "quay"
}

// resolveTimeout parses a duration string and returns it, falling back to the given duration if parsing fails.
func resolveTimeout(timeoutStr string, fallback time.Duration) time.Duration {
	if timeoutStr == "" {
		return fallback
	}
	d, err := time.ParseDuration(timeoutStr)
	if err != nil || d <= 0 {
		return fallback
	}
	return d
}

// resolveTimeoutStr validates and returns the timeout string, falling back to the default if invalid.
func resolveTimeoutStr(timeoutStr string) string {
	if timeoutStr == "" {
		return quayDefaultTimeoutStr
	}
	d, err := time.ParseDuration(timeoutStr)
	if err != nil || d <= 0 {
		return quayDefaultTimeoutStr
	}
	return timeoutStr
}

// runQuayScenario executes a single test scenario by running its entrypoint command with a timeout.
// It returns an ExtensionTestResult indicating pass, fail, or error with captured output.
func runQuayScenario(ctx context.Context, sc ScenarioSpec, scriptFS fs.FS, timeout time.Duration) *ext.ExtensionTestResult {
	result := &ext.ExtensionTestResult{
		Name: sc.Name,
	}

	argv := append([]string{sc.Entrypoint}, sc.Args...)

	runCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	out := newBoundedBuffer(maxCapturedOutputBytes)

	cmd := exec.Command(argv[0], argv[1:]...)
	cmd.Env = buildEnv(sc.EnvVars, sc.EnvFrom)
	cmd.Dir = sc.WorkDir
	cmd.Stdout = out
	cmd.Stderr = out
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err := cmd.Start(); err != nil {
		result.Result = ext.ResultFailed
		result.Error = fmt.Sprintf("failed to start scenario process: %v", err)
		result.Output = out.String()
		return result
	}

	waitErr := waitWithGracefulCancel(runCtx, cmd, quayShutdownGracePeriod)
	result.Output = out.String()

	if waitErr != nil {
		result.Result = ext.ResultFailed
		switch {
		case errors.Is(runCtx.Err(), context.DeadlineExceeded):
			result.Error = fmt.Sprintf("scenario timed out after %s: %v", timeout, waitErr)
		case errors.Is(runCtx.Err(), context.Canceled):
			result.Error = fmt.Sprintf("scenario was cancelled: %v", waitErr)
		default:
			result.Error = fmt.Sprintf("scenario exited with error: %v", waitErr)
		}
		return result
	}

	result.Result = ext.ResultPassed
	return result
}

// waitWithGracefulCancel waits for a command to complete or terminates it gracefully on context cancellation.
// It sends SIGTERM first, waits gracePeriod, then sends SIGKILL if the process hasn't exited.
func waitWithGracefulCancel(ctx context.Context, cmd *exec.Cmd, gracePeriod time.Duration) error {
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()

	select {
	case err := <-done:
		return err
	case <-ctx.Done():
		signalProcessGroup(cmd, syscall.SIGTERM)
		select {
		case err := <-done:
			return err
		case <-time.After(gracePeriod):
			signalProcessGroup(cmd, syscall.SIGKILL)
			return <-done
		}
	}
}

// signalProcessGroup sends a signal to the process group of the given command.
func signalProcessGroup(cmd *exec.Cmd, sig syscall.Signal) {
	if cmd.Process == nil {
		return
	}
	_ = syscall.Kill(-cmd.Process.Pid, sig)
}

type boundedBuffer struct {
	mu        sync.Mutex
	buf       bytes.Buffer
	maxBytes  int
	truncated bool
}

// newBoundedBuffer creates a buffer that caps output at maxBytes, discarding oldest data when full.
func newBoundedBuffer(maxBytes int) *boundedBuffer {
	return &boundedBuffer{maxBytes: maxBytes}
}

// Write implements io.Writer, appending data to the buffer and discarding excess from the front.
func (b *boundedBuffer) Write(p []byte) (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()

	n := len(p)
	b.buf.Write(p)

	if excess := b.buf.Len() - b.maxBytes; excess > 0 {
		b.buf.Next(excess)
		b.truncated = true
	}

	return n, nil
}

// String returns the buffered output, with a truncation notice if data was discarded.
func (b *boundedBuffer) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.truncated {
		return fmt.Sprintf("... [output truncated to last %d bytes] ...\n%s", b.maxBytes, b.buf.String())
	}
	return b.buf.String()
}

// buildEnv constructs an environment slice by merging os.Environ, envFrom mappings, and override values.
func buildEnv(overrides, envFrom map[string]string) []string {
	env := make(map[string]string)

	for _, kv := range os.Environ() {
		if k, v, ok := splitEnv(kv); ok {
			env[k] = v
		}
	}

	for dest, src := range envFrom {
		if dest == "" || src == "" {
			continue
		}
		if v, ok := env[src]; ok && v != "" {
			env[dest] = v
		}
	}

	for k, v := range overrides {
		env[k] = v
	}

	result := make([]string, 0, len(env))
	for k, v := range env {
		result = append(result, k+"="+v)
	}
	return result
}

// splitEnv splits a KEY=VALUE environment string into its components.
func splitEnv(kv string) (key, value string, ok bool) {
	for i := 0; i < len(kv); i++ {
		if kv[i] == '=' {
			return kv[:i], kv[i+1:], true
		}
	}
	return "", "", false
}
