package shared

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestIsSafeHost verifies that private and reserved addresses are rejected.
func TestIsSafeHost(t *testing.T) {
	blocked := []string{
		"127.0.0.1",
		"localhost",
		"10.0.0.1",
		"10.255.255.255",
		"172.16.0.1",
		"172.31.255.255",
		"192.168.0.1",
		"192.168.255.255",
		"169.254.169.254", // AWS metadata
		"[::1]",
		"::1",
	}
	for _, host := range blocked {
		if err := isSafeHost(host); err == nil {
			t.Errorf("isSafeHost(%q) should have returned an error but did not", host)
		}
	}
}

// TestValidateEmailServerRejectsPrivateHost ensures the SMTP validator refuses
// connections to private/internal addresses (SSRF guard — PROJQUAY-11645).
func TestValidateEmailServerRejectsPrivateHost(t *testing.T) {
	privateHosts := []string{
		"127.0.0.1",
		"10.0.0.1",
		"192.168.1.1",
		"169.254.169.254",
	}
	opts := Options{}
	for _, host := range privateHosts {
		ok, verr := ValidateEmailServer(opts, host, 25, false, false, "", "", "Email")
		if ok {
			t.Errorf("ValidateEmailServer(%q) should fail for private host", host)
		}
		if !strings.Contains(verr.Message, "private or reserved") {
			t.Errorf("ValidateEmailServer(%q): unexpected error message: %s", host, verr.Message)
		}
	}
}

// TestValidateLDAPServerRejectsPrivateHost ensures the LDAP validator refuses
// connections to private/internal addresses (SSRF guard — PROJQUAY-11645).
func TestValidateLDAPServerRejectsPrivateHost(t *testing.T) {
	privateURIs := []string{
		"ldap://127.0.0.1:389",
		"ldap://10.0.0.1:389",
		"ldap://192.168.1.100:389",
		"ldap://169.254.169.254:389",
	}
	opts := Options{}
	for _, uri := range privateURIs {
		ok, verr := ValidateLDAPServer(opts, uri, "cn=admin,dc=example,dc=com", "password", "uid", "mail", "", []interface{}{}, "LDAP")
		if ok {
			t.Errorf("ValidateLDAPServer(%q) should fail for private host", uri)
		}
		if !strings.Contains(verr.Message, "private or reserved") {
			t.Errorf("ValidateLDAPServer(%q): unexpected error message: %s", uri, verr.Message)
		}
	}
}

// TestValidateGitLabOAuthCredentialsInBody verifies that client_secret is NOT
// present in the request URL (CWE-598 fix — PROJQUAY-11645) and IS present in
// the POST body.
func TestValidateGitLabOAuthCredentialsInBody(t *testing.T) {
	type capture struct {
		rawQuery    string
		contentType string
		clientID    string
		secret      string
	}
	var got capture

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := r.ParseForm(); err != nil {
			t.Errorf("handler: ParseForm error: %v", err)
		}
		got = capture{
			rawQuery:    r.URL.RawQuery,
			contentType: r.Header.Get("Content-Type"),
			clientID:    r.FormValue("client_id"),
			secret:      r.FormValue("client_secret"),
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"error":"invalid_grant"}`))
	}))
	defer ts.Close()

	result := ValidateGitLabOAuth("test-client-id", "super-secret", ts.URL+"/")
	if !result {
		t.Fatal("ValidateGitLabOAuth should return true for invalid_grant response")
	}
	if strings.Contains(got.rawQuery, "client_secret") {
		t.Errorf("client_secret must not appear in the URL query string; got: %s", got.rawQuery)
	}
	if strings.Contains(got.rawQuery, "super-secret") {
		t.Errorf("client_secret value must not appear in the URL; got: %s", got.rawQuery)
	}
	if got.contentType != "application/x-www-form-urlencoded" {
		t.Errorf("expected Content-Type application/x-www-form-urlencoded, got %s", got.contentType)
	}
	if got.secret != "super-secret" {
		t.Errorf("client_secret not found in POST body; got %q", got.secret)
	}
	if got.clientID != "test-client-id" {
		t.Errorf("client_id not found in POST body; got %q", got.clientID)
	}
}

func TestValidateIsHostname(t *testing.T) {
	var tests = []struct {
		name  string
		input string
		want  bool
	}{
		// Valid FQDNs
		{"fqdn", "registry.example.com", true},
		{"fqdnWithPort", "registry.example.com:8443", true},
		{"twoParts", "fakehost.com", true},
		{"twoParts with port", "fakehost.com:443", true},
		{"subdomains", "my.registry.example.com", true},
		{"hyphenated", "my-registry.example.com", true},
		{"hyphenatedWithPort", "my-registry.example.com:5000", true},
		{"localhost", "localhost", true},
		{"localhostWithPort", "localhost:8443", true},

		// Invalid: single-label hostnames (no dots, not localhost)
		{"singleLabel", "myregistry", false},
		{"singleLabelWithPort", "myregistry:8443", false},
		{"singleLabelHyphen", "my-registry", false},
		{"singleLabelHyphenWithPort", "my-registry:8443", false},

		// Invalid: bad characters
		{"invalidChars", "registry!.com", false},
		{"spaces", "registry .com", false},
		{"underscore", "my_registry.com", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ok, err := ValidateIsHostname(tt.input, "TEST_FIELD", "TestGroup")
			if ok != tt.want {
				t.Errorf("ValidateIsHostname(%q) = %v, want %v. Error: %s", tt.input, ok, tt.want, err.Message)
			}
		})
	}
}

// TestValidateCertPairWithHostname tests the Validate function
func TestValidateCertPairWithHostname(t *testing.T) {

	certs := map[string][]byte{
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
		"ssl.cert": []byte(
			`-----BEGIN CERTIFICATE-----
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
	}

	ok, err := ValidateCertPairWithHostname(certs["ssl.cert"], certs["ssl.key"], "fakehost.com", "")
	if !ok {
		t.Error(err)
	}

}
