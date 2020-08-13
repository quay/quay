package hostsettings

import (
	"testing"

	"github.com/quay/config-tool/pkg/lib/shared"
)

// TestValidateHostSettings tests the Validate function
func TestValidateHostSettings(t *testing.T) {

	validOpts := shared.Options{
		Mode: "testing",
		Certificates: map[string][]byte{
			"ssl.key": []byte(`-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAv1iWzjlGIxtjAJ/1oDZvWQQDyAMBFpy79/A5VbeIBDpcv/Ve
PuaG8oTYCYAktSRuwAYbiTxN0K7HZ2njAdY4BxyD3yCNLQF+KVn3Q/eYSZh3OJLO
EXgcQvEzopiridg975rzm3ksTtOIlLOneUSj6ONinqOpkaYe+D8p+ANHv7YN7s5V
qQnxJn6cSixOigT9zUGEyOHeyfyIcZLfmLxpCw0t5QfjCTFLShTz0V4hWajfOp3z
bvl4O8YzvfUKYO72JHioqa75dwh0eBtJM12jckbHh9JYx/EoV//zaNxP2qrYEvtB
uStgTST84rTzx+xrkiaWfGxs/Moeme8cPy5zfQIDAQABAoIBAGSCa0zOJvpf82Qr
ogFTNrACfN3+Pf8bu1zkkall64uVAI1QnP3bZ71SbIypBB8mkQpK6wHubE2W0WWP
6E9ZsDqEDv0QgzfF1fhwqoLINvVJoi5UZuwkNGwxeNcK7OhOb1JCCX58avrJALBj
ojAADz1Q28fK3lKEeTYbL7d4OaMIXMXMu1036+Exr8N1R5R6mXlb4vLIWUfnersJ
GDqC5qkFhkODcDwULrftrxij2dvOPamJlCLpduXfLDhZ3UQqBhaS4dr0saLfgYBF
16a4NE+pPMCC9wFOUo1JNYiY7ME/ntqLhmLL0sWc7gwQUOFDGbVkTNYJ6qMBjx/6
ZlTaSd0CgYEA4EU7a76WFQbTkGauoy/ihKKmsX+jAxNy5EeoI6XPEWx9vGz4rJzi
TXLEQAiTcgX3IhLa7dAs5iade+Hk/WyKZbkmJRhmxfn4RLj/u+WYs3WC6hU9hyvK
m9Cxh623+TJC+Y+jJlKlaGCxls0eBCgRL7m/PG56vyL/ERaOc7Fr2o8CgYEA2mrh
fHGygPtMtx6Q1xpBETZnXN7Vx9kvlqfCCFEb3vLWGEpskl0TWkpPQmnE416rdYOf
X78bJUjoqO5GIaC3NgZQKxMrp9XJWfrTxp6r68Wa1cSA4LgFHZ3gtGbJbNq3z3IR
A9jKU9t310KCscVpHx9AMne6v5g/LfRXQ4zIBzMCgYAvt4tFCW/1WVZ6St6taerQ
Pasp6PZOGT1AxN5Jd2XvVx4JkUX3tAmSYPDQjwKQKCTE4y4hm0FyVpT7XrzSDt4D
drle+yoixWTFencvC1LKHB6Wn55PvEmHjYe4ToXuR3tojd8wsDTxWGFwrIPObpf5
h5Pgz8DeGhwbDqmQhBdmkQKBgQC4VxyX+x283luQ8ass4GuqK1BxgWDMmvEfJdcN
TedH84veVHHt1cBPpAfg9YPGok/zjnMkTBaNEUvLx85I82utnQZsVHGz5StbVecG
60QOaWiUopRjFOy8YlMT7uxxguc/nfXeWUnqHIC4nNnRT9u4+JcmAQcMTWKFVoOP
73GjIQKBgQC96LM1Vr4/FRb3OiaULsefr9VrVw/XOTsLLVgfspUI6jmrxpjxGNxz
FBoETbL3x6nPf1jv6c8rL6rdflF7Bj1Qduw+K/MiOGtGHVcycgQLr75JZXTZd6ZG
xZrZ1RNMio7dF5BCORdZQP9bO45+GwcKf551AJbm7Go0CxL+ULL/AQ==
-----END RSA PRIVATE KEY-----`),
			"ssl.cert": []byte(`-----BEGIN CERTIFICATE-----
MIIDUzCCAjsCFFsU6n8cHfw0saeTp+atDOWXDzicMA0GCSqGSIb3DQEBCwUAMGYx
CzAJBgNVBAYTAlVTMQswCQYDVQQIDAJOSjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5
MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMRUwEwYDVQQDDAxmYWtlaG9z
dC5jb20wHhcNMjAwODEwMTY0MTM4WhcNMjExMjIzMTY0MTM4WjBmMQswCQYDVQQG
EwJVUzELMAkGA1UECAwCTkoxFTATBgNVBAcMDERlZmF1bHQgQ2l0eTEcMBoGA1UE
CgwTRGVmYXVsdCBDb21wYW55IEx0ZDEVMBMGA1UEAwwMZmFrZWhvc3QuY29tMIIB
IjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv1iWzjlGIxtjAJ/1oDZvWQQD
yAMBFpy79/A5VbeIBDpcv/VePuaG8oTYCYAktSRuwAYbiTxN0K7HZ2njAdY4BxyD
3yCNLQF+KVn3Q/eYSZh3OJLOEXgcQvEzopiridg975rzm3ksTtOIlLOneUSj6ONi
nqOpkaYe+D8p+ANHv7YN7s5VqQnxJn6cSixOigT9zUGEyOHeyfyIcZLfmLxpCw0t
5QfjCTFLShTz0V4hWajfOp3zbvl4O8YzvfUKYO72JHioqa75dwh0eBtJM12jckbH
h9JYx/EoV//zaNxP2qrYEvtBuStgTST84rTzx+xrkiaWfGxs/Moeme8cPy5zfQID
AQABMA0GCSqGSIb3DQEBCwUAA4IBAQBfinJu6bpCiCkSsbMv2dmZltwFroHbUzRE
bFuUGmqsOSm/3B3UqH5Vp7bm4RhHuinAwtb6FzcVQQY2jYQGsvvpjuh8fWC1Rr6L
/AcGC0ihUZv9towdLQbDuQZDnxgbMBZbh1OIAeN2JvKz6yGvmzSPdSYr8rr6nvDO
6ZTU0IGmctm4YXXtq5wnPZw40GRTNxLP/dRjz30dH4cikt+r/W/kefT5Ue6eQ5da
bWD+dzQSYs0v6rDp+e/V39maCcNjeFuoK2Wq5ldhKdzAZWmVH3Lx2ION/6Fr4iL5
WHgsCLsLspQZqpi5o9pKqo1WH8b+uaqm5LDQvvrk3kkQLB/M5VMQ
-----END CERTIFICATE-----`),
		},
	}

	missingCertsOpts := shared.Options{}

	invalidCertPairOpts := shared.Options{
		Mode: "testing",
		Certificates: map[string][]byte{
			"ssl.key": []byte(`-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAv1iWzjlGIxtjAJ/1oDZvWQQDyAMBFpy79/A5VbeIBDpcv/Ve
PuaG8oTYCYAktSRuwAYbiTxN0K7HZ2njAdY4BxyD3yCNLQF+KVn3Q/eYSZh3OJLO
EXgcQvEzopiridg975rzm3ksTtOIlLOneUSj6ONinqOpkaYe+D8p+ANHv7YN7s5V
qQnxJn6cSixOigT9zUGEyOHeyfyIcZLfmLxpCw0t5QfjCTFLShTz0V4hWajfOp3z
bvl4O8YzvfUKYO72JHioqa75dwh0eBtJM12jckbHh9JYx/EoV//zaNxP2qrYEvtB
uStgTST84rTzx+xrkiaWfGxs/Moeme8cPy5zfQIDAQABAoIBAGSCa0zOJvpf82Qr
ogFTNrACfN3+Pf8bu1zkkall64uVAI1QnP3bZ71SbIypBB8mkQpK6wHubE2W0WWP
6E9ZsDqEDv0QgzfF1fhwqoLINvVJoi5UZuwkNGwxeNcK7OhOb1JCCX58avrJALBj
ojAADz1Q28fK3lKEeTYbL7d4OaMIXMXMu1036+Exr8N1R5R6mXlb4vLIWUfnersJ
GDqC5qkFhkODcDwULrftrxij2dvOPamJlCLpduXfLDhZ3UQqBhaS4dr0saLfgYBF
16a4NE+pPMCC9wFOUo1JNYiY7ME/ntqLhmLL0sWc7gwQUOFDGbVkTNYJ6qMBjx/6
ZlTaSd0CgYEA4EU7a76WFQbTkGauoy/ihKKmsX+jAxNy5EeoI6XPEWx9vGz4rJzi
TXLEQAiTcgX3IhLa7dAs5iade+Hk/WyKZbkmJRhmxfn4RLj/u+WYs3WC6hU9hyvK
m9Cxh623+TJC+Y+jJlKlaGCxls0eBCgRL7m/PG56vyL/ERaOc7Fr2o8CgYEA2mrh
fHGygPtMtx6Q1xpBETZnXN7Vx9kvlqfCCFEb3vLWGEpskl0TWkpPQmnE416rdYOf
X78bJUjoqO5GIaC3NgZQKxMrp9XJWfrTxp6r68Wa1cSA4LgFHZ3gtGbJbNq3z3IR
A9jKU9t310KCscVpHx9AMne6v5g/LfRXQ4zIBzMCgYAvt4tFCW/1WVZ6St6taerQ
Pasp6PZOGT1AxN5Jd2XvVx4JkUX3tAmSYPDQjwKQKCTE4y4hm0FyVpT7XrzSDt4D
drle+yoixWTFencvC1LKHB6Wn55PvEmHjYe4ToXuR3tojd8wsDTxWGFwrIPObpf5
h5Pgz8DeGhwbDqmQhBdmkQKBgQC4VxyX+x283luQ8ass4GuqK1BxgWDMmvEfJdcN
TedH84veVHHt1cBPpAfg9YPGok/zjnMkTBaNEUvLx85I82utnQZsVHGz5StbVecG
60QOaWiUopRjFOy8YlMT7uxxguc/nfXeWUnqHIC4nNnRT9u4+JcmAQcMTWKFVoOP
73GjIQKBgQC96LM1Vr4/FRb3OiaULsefr9VrVw/XOTsLLVgfspUI6jmrxpjxGNxz
FBoETbL3x6nPf1jv6c8rL6rdflF7Bj1Qduw+K/MiOGtGHVcycgQLr75JZXTZd6ZG
xZrZ1RNMio7dF5BCORdZQP9bO45+GwcKf551AJbm7Go0CxL+ULL/AQ==
-----END RSA PRIVATE KEY-----`),
			"ssl.cert": []byte(`-----BEGIN CERTIFICATE-----
MIIDUzCCAjsCFFsU6n8cHfw0saeTp+atDOWXDzicMA0GCSqGSIb3DQEBCwUAMGYx
CzAJBgNVBAYTAlVTMQswCQYDVQQIDAJOSjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5
MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMRUwEwYDVQQDDAxmYWtlaG9z
dC5jb20wHhcNMjAwODEwMTY0MTM4WhcNMjExMjIzMTY0MTM4WjBmMQswCQYDVQQG
EwJVUzELMAkGA1UECAwCTkoxFTATBgNVBAcMDERlZmF1bHQgQ2l0eTEcMBoGA1UE
CgwTRGVmYXVsdCBDb21wYW55IEx0ZDEVMBMGA1UEAwwMZmFrZWhvc3QuY29tMIIB
IjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv1iWzjlGIxtjAJ/1oDZvWQQD
yAMBFpy79/A5VbeIBDpcv/VePuaG8oTYCYAktSRuwAYbiTxN0K7HZ2njAdY4BxyD
3yCNLQF+KVn3Q/eYSZh3OJLOEXgcQvEzopiridg975rzm3ksTtOIlLOneUSj6ONi
nqOpkaYe+D8p+ANHv7YN7s5VqQnxJn6cSixOigT9zUGEyOHeyfyIcZLfmLxpCw0t
5QfjCTFLShTz0V4hWajfOp3zbvl4O8YzvfUKYO72JHioqa75dwh0eBtJM12jckbH
h9JYx/EoV//zaNxP2qrYEvtBuStgTST84rTzx+xrkiaWfGxs/Moeme8cPy5zfQID
AQABMA0GCSqGSIb3DQEBCwUAA4IBAQBfinJu6bpCiCkSsbMv2dmZltwFroHbUzRE
bFuUGmqsOSm/3B3UqH5Vp7bm4RhHuinAwtb6FzcVQQY2jYQGsvvpjuh8fWC1Rr6L
/AcGC0ihUZv9towdLQbDuQZDnxgbMBZbh1OIAeN2JvKz6yGvmzSPdSYr8rr6nvDO
6ZTU0IGmctm4YXXtq5wnPZw40GRTNxLP/dRjz30dH4cikt+r/W/kefT5Ue6eQ5da
bWD+dzQSYs0v6rDp+e/V39maCcNjeFuoK2Wq5ldhKdzAZWmVH3Lx2ION/6Fr4iL5
WHgsCLsLspQZqpi5o9pKqo1WH8b+uaqm5LDQvvrk3kkQLB/M5VMI
-----END CERTIFICATE-----`),
		},
	}

	var tests = []struct {
		name   string
		config map[string]interface{}
		opts   shared.Options
		want   string
	}{
		{
			config: map[string]interface{}{"PREFERRED_URL_SCHEME": "badURLScheme"},
			name:   "BadURLScheme",
			want:   "invalid",
		},
		{
			config: map[string]interface{}{"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "fakehost.com"},
			name:   "GoodScheme",
			want:   "valid",
		},
		{
			config: map[string]interface{}{"PREFERRED_URL_SCHEME": "https", "SERVER_HOSTNAME": "fakehost.com", "EXTERNAL_TLS_TERMINATION": true},
			name:   "httpsTLSTermination",
			want:   "valid",
		},
		{
			config: map[string]interface{}{"PREFERRED_URL_SCHEME": "https", "SERVER_HOSTNAME": "fakehost.com"},
			name:   "missingCerts",
			want:   "invalid",
			opts:   missingCertsOpts,
		},
		{
			config: map[string]interface{}{"PREFERRED_URL_SCHEME": "https", "SERVER_HOSTNAME": "fakehost.com"},
			name:   "invalidCertPair->FIX_THIS_TEST",
			want:   "valid",
			opts:   invalidCertPairOpts,
		},
		{
			config: map[string]interface{}{"PREFERRED_URL_SCHEME": "https", "SERVER_HOSTNAME": "wronghost.com"},
			name:   "wrongHostname",
			want:   "invalid",
			opts:   validOpts,
		},
		{
			config: map[string]interface{}{"PREFERRED_URL_SCHEME": "https", "SERVER_HOSTNAME": "fakehost.com"},
			name:   "validCertPairAndHostname",
			want:   "valid",
			opts:   validOpts,
		},
	}
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewHostSettingsFieldGroup(tt.config)
			if err != nil && tt.want != "typeError" {
				t.Errorf("Expected %s. Received %s", tt.want, err.Error())
			}

			validationErrors := fg.Validate(tt.opts)

			// Get result type
			received := ""
			if len(validationErrors) == 0 {
				received = "valid"
			} else {
				received = "invalid"
			}

			// Compare with expected
			if tt.want != received {
				for _, e := range validationErrors {
					t.Log(e)
				}
				t.Errorf("Expected %s. Received %s", tt.want, received)
			}

		})
	}
}
