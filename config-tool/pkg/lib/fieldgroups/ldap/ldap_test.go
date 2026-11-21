package ldap

import (
	"bufio"
	"net"
	"testing"

	ber "github.com/go-asn1-ber/asn1-ber"
	ldaplib "github.com/go-ldap/ldap/v3"

	"github.com/quay/quay/config-tool/pkg/lib/shared"
)

// mockLDAPDial returns a dial function that directs every LDAP connection to
// an in-process stub server instead of an external host. The stub accepts
// simple binds whose password equals correctPassword and rejects all others;
// it returns success for every subsequent search request.
func mockLDAPDial(correctPassword string) func(string, ...ldaplib.DialOpt) (*ldaplib.Conn, error) {
	return func(_ string, _ ...ldaplib.DialOpt) (*ldaplib.Conn, error) {
		serverConn, clientConn := net.Pipe()
		go serveMockLDAP(serverConn, correctPassword)
		conn := ldaplib.NewConn(clientConn, false)
		conn.Start()
		return conn, nil
	}
}

// serveMockLDAP reads LDAP packets from conn and writes minimal BER-encoded
// LDAP responses. It closes conn when it has nothing more to send.
func serveMockLDAP(conn net.Conn, correctPassword string) {
	defer conn.Close()
	buf := bufio.NewReader(conn)
	for {
		pkt, err := ber.ReadPacket(buf)
		if err != nil {
			return
		}
		if len(pkt.Children) < 2 {
			return
		}
		msgID := pkt.Children[0].Value.(int64)
		op := pkt.Children[1]

		switch op.Tag {
		case ldaplib.ApplicationBindRequest: // 0
			gotPwd := ""
			if len(op.Children) >= 3 {
				gotPwd = string(op.Children[2].Data.Bytes())
			}
			resultCode := int64(ldaplib.LDAPResultSuccess)
			if gotPwd != correctPassword {
				resultCode = int64(ldaplib.LDAPResultInvalidCredentials)
			}
			resp := makeLDAPResult(msgID, ber.Tag(ldaplib.ApplicationBindResponse), resultCode)
			conn.Write(resp.Bytes()) //nolint:errcheck
			if resultCode != 0 {
				return
			}

		case ldaplib.ApplicationSearchRequest: // 3
			resp := makeLDAPResult(msgID, ber.Tag(ldaplib.ApplicationSearchResultDone), int64(ldaplib.LDAPResultSuccess))
			conn.Write(resp.Bytes()) //nolint:errcheck
			return

		default:
			return
		}
	}
}

// makeLDAPResult encodes a minimal LDAPMessage envelope containing an
// application-tagged result sequence with the given resultCode, empty
// matchedDN, and empty diagnosticMessage.
func makeLDAPResult(msgID int64, appTag ber.Tag, resultCode int64) *ber.Packet {
	envelope := ber.Encode(ber.ClassUniversal, ber.TypeConstructed, ber.TagSequence, nil, "LDAPMessage")
	envelope.AppendChild(ber.NewInteger(ber.ClassUniversal, ber.TypePrimitive, ber.TagInteger, msgID, "MessageID"))

	response := ber.Encode(ber.ClassApplication, ber.TypeConstructed, appTag, nil, "Response")
	response.AppendChild(ber.NewInteger(ber.ClassUniversal, ber.TypePrimitive, ber.TagEnumerated, resultCode, "resultCode"))
	response.AppendChild(ber.NewString(ber.ClassUniversal, ber.TypePrimitive, ber.TagOctetString, "", "matchedDN"))
	response.AppendChild(ber.NewString(ber.ClassUniversal, ber.TypePrimitive, ber.TagOctetString, "", "diagnosticMessage"))

	envelope.AppendChild(response)
	return envelope
}

// TestValidateLDAP tests the Validate function using an in-process LDAP stub
// server. The stub accepts binds with password "password" and rejects all
// others, so no external network connectivity is required.
func TestValidateLDAP(t *testing.T) {
	// correctPassword is the admin password the stub LDAP server will accept.
	const correctPassword = "password"
	mockDial := mockLDAPDial(correctPassword)

	var tests = []struct {
		name   string
		config map[string]interface{}
		want   string
	}{
		{
			name:   "wrongAuthType",
			config: map[string]interface{}{"AUTHENTICATION_TYPE": "Database"},
			want:   "valid",
		},
		{
			name:   "noValidAuthSettings",
			config: map[string]interface{}{"AUTHENTICATION_TYPE": "LDAP"},
			want:   "invalid",
		},
		{
			name: "validAuthSettings",
			config: map[string]interface{}{
				"AUTHENTICATION_TYPE": "LDAP",
				"LDAP_URI":            "ldap://ldap.example.com",
				"LDAP_BASE_DN":        []interface{}{"dc=example", "dc=com"},
				"LDAP_ADMIN_DN":       "cn=read-only-admin,dc=example,dc=com",
				"LDAP_ADMIN_PASSWD":   correctPassword,
				"LDAP_USER_RDN":       []interface{}{},
				"LDAP_USER_FILTER":    "(uid=newton)",
			},
			want: "valid",
		},
		{
			name: "invalidPassword",
			config: map[string]interface{}{
				"AUTHENTICATION_TYPE": "LDAP",
				"LDAP_URI":            "ldap://ldap.example.com",
				"LDAP_BASE_DN":        []interface{}{"dc=example", "dc=com"},
				"LDAP_ADMIN_DN":       "cn=read-only-admin,dc=example,dc=com",
				"LDAP_ADMIN_PASSWD":   "wrongpassword",
				"LDAP_USER_RDN":       []interface{}{},
				"LDAP_USER_FILTER":    "(CN=hey)",
			},
			want: "invalid",
		},
		{
			name: "userExists",
			config: map[string]interface{}{
				"AUTHENTICATION_TYPE": "LDAP",
				"LDAP_URI":            "ldap://ldap.example.com",
				"LDAP_BASE_DN":        []interface{}{"dc=example", "dc=com"},
				"LDAP_ADMIN_DN":       "cn=read-only-admin,dc=example,dc=com",
				"LDAP_ADMIN_PASSWD":   correctPassword,
				"LDAP_USER_RDN":       []interface{}{},
				"LDAP_USER_FILTER":    "",
			},
			want: "valid",
		},
	}
	for _, tt := range tests {

		// Run specific test
		t.Run(tt.name, func(t *testing.T) {

			// Get validation result
			fg, err := NewLDAPFieldGroup(tt.config)
			if err != nil && tt.want != "typeError" {
				t.Errorf("Expected %s. Received %s", tt.want, err.Error())
			}

			opts := shared.Options{
				LDAPDialFunc: mockDial,
			}

			validationErrors := fg.Validate(opts)

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
