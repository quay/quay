package system

import (
	"net"
	"strings"
)

// HostnameWithoutPort removes a valid port and IPv6 brackets from a hostname.
func HostnameWithoutPort(hostname string) string {
	if host, _, err := net.SplitHostPort(hostname); err == nil {
		hostname = host
	}
	return strings.Trim(hostname, "[]")
}
