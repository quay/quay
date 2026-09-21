package shared

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func makeGarageMockServer(t *testing.T) (url string, locationCalled *bool) {
	called := false
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Logf("Called method: %s", r.Method)
		t.Logf("Endpoint: %s", r.RequestURI)
		t.Logf("Params: %s", r.URL.RawQuery)
		t.Logf("Headers: %v", r.Header)
		if strings.Contains(r.URL.RawQuery, "location") {
			called = true
			// Garage returns 400 when scope is wrong
			w.Header().Set("Content-type", "application/xml")
			w.WriteHeader(http.StatusBadRequest)
			w.Write([]byte(`<?xml version="1.0"?><Error><Code>AuthorizationHeaderMalformed</code>` +
				`<Message>unexpected scope</Message></Error>`))
			return
		}
		if strings.Contains(r.Header.Get("Authorization"), "failimmediately") {
			w.Header().Set("Content-type", "application/xml")
			w.WriteHeader(http.StatusBadRequest)
			w.Write([]byte(`<?xml version="1.0"?><Error><Code>InternalError</Code>` +
				`<Message>Internal server error</Message></Error>`))
			return
		}
		if r.Method == http.MethodGet {
			w.WriteHeader(http.StatusOK)
		}
	}))
	t.Cleanup(srv.Close)
	return srv.URL, &called
}

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

// Call validateMinioGateway with region set: bypasses GetBucketLocation on storage side and issues an immediate HEAD
// on the bucket.
func TestValidateMinioGatewayWithRegionSkipsLocationDetection(t *testing.T) {
	srvURL, locationCalled := makeGarageMockServer(t)
	host := strings.TrimPrefix(srvURL, "http://")
	ok, err := validateMinioGateway(Options{Mode: "online"}, "test", host, "garage", "key", "secret", "bucket", "", false, "fg")

	if !ok {
		t.Fatalf("expected validation to pass: %v", err.Message)
	}

	if *locationCalled {
		t.Error("GetBucketLocation was called, despite region being explicitly set")
	}
}

// Regression test: Call validateMinioGateway without region set: GetBucketLocation is invoked with a 'GET' to determine
// location which should raise a 400 (swallowed), then calls HeadBucket which passes incorrectly (due to 400).
func TestValidateMinioGatewayWithoutRegionDoesNotSkipLocationDetection(t *testing.T) {
	srvURL, locationCalled := makeGarageMockServer(t)
	host := strings.TrimPrefix(srvURL, "http://")

	validateMinioGateway(Options{Mode: "online"}, "test", host, "", "key", "secret", "bucket", "", false, "fg")

	if !*locationCalled {
		t.Error("Expected GetBucketLocation to be called because region is not set")
	}
}

// Validates that the full storage validation path correctly reads the region_name from provided storage arguments.
func TestValidateStorageRadosGWRegionName(t *testing.T) {
	srvURL, locationCalled := makeGarageMockServer(t)
	host := strings.TrimPrefix(srvURL, "http://")

	args := &DistributedStorageArgs{
		AccessKey:  "key",
		SecretKey:  "secret",
		Hostname:   host,
		BucketName: "bucket",
		RegionName: "garage",
	}

	ok, err := ValidateStorage(Options{Mode: "Online"}, "test", "RadosGWStorage", args, "fg")

	if !ok {
		t.Fatalf("expected validation to pass: %v", err)
	}

	if *locationCalled {
		t.Error("GetBucketLocation was called despite region_name was set.")
	}
}

// Verify that the errors are still propagating properly.
func TestValidateStorageRadosGWInternalServerError(t *testing.T) {
	srvURL, _ := makeGarageMockServer(t)
	host := strings.TrimPrefix(srvURL, "http://")

	args := &DistributedStorageArgs{
		AccessKey:  "key",
		SecretKey:  "secret",
		Hostname:   host,
		BucketName: "bucket",
		RegionName: "failimmediately",
	}

	ok, err := ValidateStorage(Options{Mode: "Online"}, "test", "RadosGWStorage", args, "fg")

	assert.False(t, ok)
	t.Logf("received error: %s", err[0].Message)
	assert.Contains(t, err[0].Message, "Bad Request")
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
