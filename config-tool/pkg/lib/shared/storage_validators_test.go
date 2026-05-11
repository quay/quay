package shared

import (
	"testing"
)

func TestBuildEndpoint(t *testing.T) {
	tests := []struct {
		name            string
		endpointURL     string
		host            string
		port            int
		defaultIsSecure bool
		wantEndpoint    string
		wantIsSecure    bool
		wantErr         bool
	}{
		{
			name:            "https scheme in endpoint_url forces isSecure=true",
			endpointURL:     "https://s3.ap-southeast-2.amazonaws.com",
			defaultIsSecure: false,
			wantEndpoint:    "s3.ap-southeast-2.amazonaws.com",
			wantIsSecure:    true,
		},
		{
			name:            "http scheme in endpoint_url forces isSecure=false",
			endpointURL:     "http://minio.internal:9000",
			defaultIsSecure: true,
			wantEndpoint:    "minio.internal:9000",
			wantIsSecure:    false,
		},
		{
			name:            "no scheme in endpoint_url uses defaultIsSecure=true",
			endpointURL:     "s3.amazonaws.com",
			defaultIsSecure: true,
			wantEndpoint:    "s3.amazonaws.com",
			wantIsSecure:    true,
		},
		{
			name:            "no scheme in endpoint_url uses defaultIsSecure=false",
			endpointURL:     "minio.internal",
			defaultIsSecure: false,
			wantEndpoint:    "minio.internal",
			wantIsSecure:    false,
		},
		{
			name:            "host with port uses defaultIsSecure",
			host:            "minio.internal",
			port:            9000,
			defaultIsSecure: true,
			wantEndpoint:    "minio.internal:9000",
			wantIsSecure:    true,
		},
		{
			// Regression test for PROJQUAY-11486: host-based S3Storage config with is_secure=false
			// must still resolve to isSecure=true when defaultIsSecure=true is passed by the caller.
			name:            "host with is_secure=false, defaultIsSecure=true yields HTTPS (S3Storage fix)",
			host:            "s3.ap-southeast-2.amazonaws.com",
			defaultIsSecure: true,
			wantEndpoint:    "s3.ap-southeast-2.amazonaws.com",
			wantIsSecure:    true,
		},
		{
			name:    "neither endpoint_url nor host returns error",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			endpoint, isSecure, err := buildEndpoint(tt.endpointURL, tt.host, tt.port, tt.defaultIsSecure)
			if (err != nil) != tt.wantErr {
				t.Fatalf("buildEndpoint() error = %v, wantErr %v", err, tt.wantErr)
			}
			if tt.wantErr {
				return
			}
			if endpoint != tt.wantEndpoint {
				t.Errorf("endpoint = %q, want %q", endpoint, tt.wantEndpoint)
			}
			if isSecure != tt.wantIsSecure {
				t.Errorf("isSecure = %v, want %v", isSecure, tt.wantIsSecure)
			}
		})
	}
}

func TestBuildSTSEndpointConfig(t *testing.T) {
	tests := []struct {
		name            string
		args            *DistributedStorageArgs
		defaultIsSecure bool
		wantEndpoint    string
		wantIsSecure    bool
		wantErr         bool
	}{
		{
			// Regression test for PROJQUAY-11486: S3Storage passes defaultIsSecure=true so that
			// a host-based config with is_secure=false still validates over HTTPS, matching the
			// Python S3Storage backend which hardcodes is_secure=True.
			name: "S3Storage with host and is_secure=false uses HTTPS when defaultIsSecure=true",
			args: &DistributedStorageArgs{
				Host:     "s3.ap-southeast-2.amazonaws.com",
				IsSecure: false,
			},
			defaultIsSecure: true,
			wantEndpoint:    "s3.ap-southeast-2.amazonaws.com",
			wantIsSecure:    true,
		},
		{
			name: "explicit http:// endpoint_url overrides defaultIsSecure=true",
			args: &DistributedStorageArgs{
				EndpointURL: "http://minio.internal:9000",
			},
			defaultIsSecure: true,
			wantEndpoint:    "minio.internal:9000",
			wantIsSecure:    false,
		},
		{
			name: "no endpoint falls back to s3.amazonaws.com with HTTPS",
			args: &DistributedStorageArgs{},
			// defaultIsSecure value doesn't matter for the no-endpoint path
			defaultIsSecure: false,
			wantEndpoint:    "s3.amazonaws.com",
			wantIsSecure:    true,
		},
		{
			name: "STSS3Storage with is_secure=false preserves HTTP when defaultIsSecure=false",
			args: &DistributedStorageArgs{
				Host:     "sts.internal",
				IsSecure: false,
			},
			defaultIsSecure: false,
			wantEndpoint:    "sts.internal",
			wantIsSecure:    false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			endpoint, isSecure, _, err := buildSTSEndpointConfig(tt.args, tt.defaultIsSecure)
			if (err != nil) != tt.wantErr {
				t.Fatalf("buildSTSEndpointConfig() error = %v, wantErr %v", err, tt.wantErr)
			}
			if tt.wantErr {
				return
			}
			if endpoint != tt.wantEndpoint {
				t.Errorf("endpoint = %q, want %q", endpoint, tt.wantEndpoint)
			}
			if isSecure != tt.wantIsSecure {
				t.Errorf("isSecure = %v, want %v", isSecure, tt.wantIsSecure)
			}
		})
	}
}
