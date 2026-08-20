package system

import (
	"context"
	"fmt"
	"testing"
)

type fakeCgroupRunner struct {
	output string
	err    error
}

func (f *fakeCgroupRunner) Run(_ context.Context, _ string, _ ...string) error {
	return f.err
}

func (f *fakeCgroupRunner) Output(_ context.Context, _ string, _ ...string) (string, error) {
	return f.output, f.err
}

func TestCheckCgroupVersion(t *testing.T) {
	tests := []struct {
		name    string
		output  string
		err     error
		want    string
		wantErr bool
	}{
		{name: "v2", output: "v2\n", want: "v2"},
		{name: "v1", output: "v1\n", want: "v1"},
		{name: "v2 no newline", output: "v2", want: "v2"},
		{name: "podman not found", err: fmt.Errorf("exec: podman: not found"), wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := CheckCgroupVersion(context.Background(), &fakeCgroupRunner{output: tt.output, err: tt.err})
			if (err != nil) != tt.wantErr {
				t.Fatalf("CheckCgroupVersion() error = %v, wantErr %v", err, tt.wantErr)
			}
			if got != tt.want {
				t.Errorf("CheckCgroupVersion() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestValidateCgroupsForQuadlet(t *testing.T) {
	tests := []struct {
		name    string
		output  string
		err     error
		wantErr bool
	}{
		{name: "v2 passes", output: "v2", wantErr: false},
		{name: "podman unavailable passes", err: fmt.Errorf("not found"), wantErr: false},
		// v1 rootful/rootless behavior depends on os.Getuid() which we
		// cannot fake in unit tests without build tags. The rootless v1
		// path is covered by integration tests (PROJQUAY-12523 test 2).
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateCgroupsForQuadlet(context.Background(), &fakeCgroupRunner{output: tt.output, err: tt.err})
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateCgroupsForQuadlet() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
