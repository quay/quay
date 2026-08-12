package system

import (
	"fmt"
	"net"
	"strconv"
	"strings"
)

// HostnameWithoutPort removes a valid port and IPv6 brackets from a hostname.
func HostnameWithoutPort(hostname string) (string, error) {
	if hostname == "" {
		return "", fmt.Errorf("hostname is empty")
	}

	host, port, splitErr := net.SplitHostPort(hostname)
	if splitErr == nil {
		if host == "" {
			return "", fmt.Errorf("hostname in %q is empty", hostname)
		}
		if strings.ContainsAny(hostname, "[]") {
			if !strings.HasPrefix(hostname, "[") || !validIPv6Hostname(host) {
				return "", fmt.Errorf("invalid bracketed IPv6 hostname %q", hostname)
			}
		}
		if err := validateHostnamePort(port); err != nil {
			return "", fmt.Errorf("invalid port in hostname %q: %w", hostname, err)
		}
		return host, nil
	}

	if strings.ContainsAny(hostname, "[]") {
		if !strings.HasPrefix(hostname, "[") || !strings.HasSuffix(hostname, "]") {
			return "", fmt.Errorf("invalid bracket syntax in hostname %q", hostname)
		}
		host = strings.TrimSuffix(strings.TrimPrefix(hostname, "["), "]")
		if !validIPv6Hostname(host) {
			return "", fmt.Errorf("invalid bracketed IPv6 hostname %q", hostname)
		}
		return host, nil
	}

	if strings.Contains(hostname, ":") && net.ParseIP(hostname) == nil {
		return "", fmt.Errorf("parse hostname %q: %w", hostname, splitErr)
	}
	return hostname, nil
}

func validIPv6Hostname(hostname string) bool {
	return strings.Contains(hostname, ":") && net.ParseIP(hostname) != nil
}

func validateHostnamePort(port string) error {
	if port == "" {
		return fmt.Errorf("port is empty")
	}
	for _, character := range port {
		if character < '0' || character > '9' {
			return fmt.Errorf("port %q is not numeric", port)
		}
	}
	parsed, err := strconv.ParseUint(port, 10, 16)
	if err != nil || parsed == 0 {
		return fmt.Errorf("port %q is outside 1-65535", port)
	}
	return nil
}
