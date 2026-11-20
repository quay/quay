package adapter

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"testing/fstest"
	"time"

	ext "github.com/openshift-eng/openshift-tests-extension/pkg/extension/extensiontests"
)

func TestValidateScenarioSpec(t *testing.T) {
	tests := []struct {
		name    string
		spec    ScenarioSpec
		wantErr string
	}{
		{
			name:    "missing name",
			spec:    ScenarioSpec{Entrypoint: "/bin/bash"},
			wantErr: "missing name",
		},
		{
			name:    "missing entrypoint",
			spec:    ScenarioSpec{Name: "[sig-quay] t"},
			wantErr: "must set entrypoint",
		},
		{
			name: "valid",
			spec: ScenarioSpec{Name: "[sig-quay] t", Entrypoint: "/bin/bash"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateScenarioSpec(tt.spec)
			if tt.wantErr == "" {
				if err != nil {
					t.Fatalf("expected no error, got %v", err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("expected error containing %q, got %v", tt.wantErr, err)
			}
		})
	}
}

func TestCodeLocation(t *testing.T) {
	if got := codeLocation(ScenarioSpec{Entrypoint: "/bin/bash", WorkDir: "/tmp"}); got != "/tmp /bin/bash" {
		t.Errorf("workdir+entrypoint: got %q", got)
	}
	if got := codeLocation(ScenarioSpec{Entrypoint: "/bin/bash"}); got != "/bin/bash" {
		t.Errorf("entrypoint only: got %q", got)
	}
	if got := codeLocation(ScenarioSpec{}); got != "" {
		t.Errorf("empty: got %q", got)
	}
}

func TestGetComponent(t *testing.T) {
	if got := getComponent(); got != "quay" {
		t.Errorf("got %q, want quay", got)
	}
}

func TestResolveTimeout(t *testing.T) {
	fallback := 5 * time.Minute
	tests := []struct {
		in   string
		want time.Duration
	}{
		{"", fallback},
		{"10m", 10 * time.Minute},
		{"90s", 90 * time.Second},
		{"garbage", fallback},
		{"0s", fallback},
		{"-5s", fallback},
	}
	for _, tt := range tests {
		if got := resolveTimeout(tt.in, fallback); got != tt.want {
			t.Errorf("resolveTimeout(%q) = %v, want %v", tt.in, got, tt.want)
		}
	}
}

func TestResolveTimeoutStr(t *testing.T) {
	tests := []struct {
		in   string
		want string
	}{
		{"", quayDefaultTimeoutStr},
		{"10m", "10m"},
		{"garbage", quayDefaultTimeoutStr},
		{"0s", quayDefaultTimeoutStr},
	}
	for _, tt := range tests {
		if got := resolveTimeoutStr(tt.in); got != tt.want {
			t.Errorf("resolveTimeoutStr(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}

func TestSplitEnv(t *testing.T) {
	if k, v, ok := splitEnv("KEY=value"); !ok || k != "KEY" || v != "value" {
		t.Errorf("splitEnv(KEY=value) = %q, %q, %v", k, v, ok)
	}
	if _, _, ok := splitEnv("NOEQUALS"); ok {
		t.Error("splitEnv(NOEQUALS) should not be ok")
	}
}

func envMap(env []string) map[string]string {
	m := make(map[string]string, len(env))
	for _, kv := range env {
		if k, v, ok := splitEnv(kv); ok {
			m[k] = v
		}
	}
	return m
}

func TestBuildEnv(t *testing.T) {
	t.Setenv("ADAPTER_TEST_AMBIENT", "ambient-value")
	t.Setenv("ADAPTER_TEST_CONFLICT", "ambient-original")

	env := buildEnv(
		map[string]string{
			"ADAPTER_TEST_CONFLICT": "declared-wins",
			"ADAPTER_TEST_OVERRIDE": "overridden",
		},
		map[string]string{
			"ADAPTER_TEST_COPIED":  "ADAPTER_TEST_AMBIENT",
			"ADAPTER_TEST_MISSING": "ADAPTER_TEST_DOES_NOT_EXIST",
			"":                     "ignored",
		},
	)
	m := envMap(env)

	if m["ADAPTER_TEST_AMBIENT"] != "ambient-value" {
		t.Errorf("ambient undeclared not preserved: %v", m["ADAPTER_TEST_AMBIENT"])
	}
	if m["ADAPTER_TEST_OVERRIDE"] != "overridden" {
		t.Errorf("override not applied: %v", m["ADAPTER_TEST_OVERRIDE"])
	}
	if m["ADAPTER_TEST_CONFLICT"] != "declared-wins" {
		t.Errorf("declared value should override ambient: got %v want declared-wins", m["ADAPTER_TEST_CONFLICT"])
	}
	if m["ADAPTER_TEST_COPIED"] != "ambient-value" {
		t.Errorf("envFrom copy not applied: %v", m["ADAPTER_TEST_COPIED"])
	}
	if _, ok := m["ADAPTER_TEST_MISSING"]; ok {
		t.Error("envFrom with missing source should be skipped")
	}
}

func TestBoundedBuffer(t *testing.T) {
	b := newBoundedBuffer(10)
	if _, err := b.Write([]byte("hello")); err != nil {
		t.Fatalf("write: %v", err)
	}
	if got := b.String(); got != "hello" {
		t.Errorf("small write: got %q", got)
	}

	b2 := newBoundedBuffer(10)
	if _, err := b2.Write([]byte("0123456789ABCDEF")); err != nil {
		t.Fatalf("write: %v", err)
	}
	got := b2.String()
	if !strings.Contains(got, "output truncated to last 10 bytes") {
		t.Errorf("truncation notice missing: %q", got)
	}
	if !strings.HasSuffix(got, "6789ABCDEF") {
		t.Errorf("expected the last 10 bytes to be retained, got %q", got)
	}
}

func TestMaterializeFS(t *testing.T) {
	fsys := fstest.MapFS{
		"scripts/check.sh": &fstest.MapFile{Data: []byte("#!/bin/bash\n")},
		"scenarios.json":   &fstest.MapFile{Data: []byte("[]")},
	}
	dir := t.TempDir()
	if err := materializeFS(fsys, dir); err != nil {
		t.Fatalf("materializeFS: %v", err)
	}

	shInfo, err := os.Stat(filepath.Join(dir, "scripts", "check.sh"))
	if err != nil {
		t.Fatalf("script not materialized: %v", err)
	}
	if perm := shInfo.Mode().Perm(); perm != 0755 {
		t.Errorf("script perm = %o, want 755", perm)
	}

	jsonInfo, err := os.Stat(filepath.Join(dir, "scenarios.json"))
	if err != nil {
		t.Fatalf("json not materialized: %v", err)
	}
	if perm := jsonInfo.Mode().Perm(); perm != 0644 {
		t.Errorf("json perm = %o, want 644", perm)
	}
}

func TestBuildExtensionTestSpecsFromQuayScenarios(t *testing.T) {
	meta := []byte(`[
	  {"name":"[sig-quay] pass","entrypoint":"/bin/sh","args":["-c","exit 0"],"tags":["SMOKE"],"timeout":"200ms"},
	  {"name":"[sig-quay] informing","entrypoint":"/bin/sh","args":["-c","exit 0"],"informing":true}
	]`)
	specs, err := BuildExtensionTestSpecsFromQuayScenarios(meta, nil)
	if err != nil {
		t.Fatalf("build: %v", err)
	}
	if len(specs) != 2 {
		t.Fatalf("expected 2 specs, got %d", len(specs))
	}
	if specs[0].Name != "[sig-quay] pass" {
		t.Errorf("spec name: %q", specs[0].Name)
	}
	if specs[0].Tags["component"] != "quay" {
		t.Errorf("component tag: %v", specs[0].Tags["component"])
	}
	if specs[0].Tags["SMOKE"] != "true" {
		t.Errorf("SMOKE tag: %v", specs[0].Tags["SMOKE"])
	}
	if specs[0].Timeout != 200*time.Millisecond {
		t.Errorf("timeout: %v", specs[0].Timeout)
	}
	if specs[0].Lifecycle != ext.LifecycleBlocking {
		t.Errorf("expected blocking lifecycle for default spec")
	}
	if specs[1].Lifecycle != ext.LifecycleInforming {
		t.Errorf("expected informing lifecycle for informing spec")
	}

	if _, err := BuildExtensionTestSpecsFromQuayScenarios([]byte("{not json"), nil); err == nil {
		t.Error("invalid JSON should return an error")
	}
	if _, err := BuildExtensionTestSpecsFromQuayScenarios([]byte(`[{"entrypoint":"/bin/sh"}]`), nil); err == nil {
		t.Error("missing name should return an error")
	}
}

// runResult runs a scenario spec and returns its result.
func runResult(t *testing.T, spec *ext.ExtensionTestSpec) *ext.ExtensionTestResult {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	return spec.Run(ctx)
}

func TestRunQuayScenarioOutcomes(t *testing.T) {
	meta := []byte(`[
	  {"name":"[sig-quay] pass","entrypoint":"/bin/sh","args":["-c","echo hello"],"timeout":"30s"},
	  {"name":"[sig-quay] fail","entrypoint":"/bin/sh","args":["-c","echo boom >&2; exit 3"],"timeout":"30s"},
	  {"name":"[sig-quay] skip","entrypoint":"/bin/sh","args":["-c","exit 2"],"timeout":"30s"}
	]`)
	specs, err := BuildExtensionTestSpecsFromQuayScenarios(meta, nil)
	if err != nil {
		t.Fatalf("build: %v", err)
	}

	r := runResult(t, specs[0])
	if r.Result != ext.ResultPassed {
		t.Errorf("pass scenario: result=%v error=%v output=%q", r.Result, r.Error, r.Output)
	}
	if !strings.Contains(r.Output, "hello") {
		t.Errorf("pass scenario output missing stdout: %q", r.Output)
	}

	r = runResult(t, specs[1])
	if r.Result != ext.ResultFailed {
		t.Errorf("fail scenario: result=%v", r.Result)
	}
	if !strings.Contains(r.Output, "boom") {
		t.Errorf("fail scenario output missing stderr: %q", r.Output)
	}

	r = runResult(t, specs[2])
	if r.Result != ext.ResultSkipped {
		t.Errorf("exit-2 scenario: result=%v (want skipped)", r.Result)
	}
}

// TestRunQuayScenarioTimeout verifies the graceful-shutdown path: a scenario
// that overruns its timeout must terminate promptly (SIGTERM to the process
// group) and report a failure, never hang until the go test deadline.
func TestRunQuayScenarioTimeout(t *testing.T) {
	meta := []byte(`[{"name":"[sig-quay] slow","entrypoint":"/bin/sh","args":["-c","sleep 30"],"timeout":"200ms"}]`)
	specs, err := BuildExtensionTestSpecsFromQuayScenarios(meta, nil)
	if err != nil {
		t.Fatalf("build: %v", err)
	}

	start := time.Now()
	r := runResult(t, specs[0])
	elapsed := time.Since(start)

	if r.Result != ext.ResultFailed {
		t.Errorf("timed-out scenario: result=%v (want failed)", r.Result)
	}
	if elapsed > 15*time.Second {
		t.Errorf("timed-out scenario took %v to terminate; graceful shutdown did not fire", elapsed)
	}
}
