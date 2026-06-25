package installer

import (
	"fmt"
	"net"
	"strings"
)

// ValidateHostname checks that hostname is a valid DNS name or IP address.
func ValidateHostname(hostname string) error {
	if len(hostname) > 253 {
		return fmt.Errorf("exceeds 253 characters (got %d)", len(hostname))
	}
	if net.ParseIP(hostname) != nil {
		return nil
	}
	labels := strings.Split(hostname, ".")
	for _, label := range labels {
		if label == "" {
			return fmt.Errorf("contains empty label")
		}
		if len(label) > 63 {
			return fmt.Errorf("label %q exceeds 63 characters", label)
		}
		if !isASCIIAlnum(rune(label[0])) || !isASCIIAlnum(rune(label[len(label)-1])) {
			return fmt.Errorf("label %q must start and end with alphanumeric character", label)
		}
		for _, c := range label {
			if !isASCIIAlnum(c) && c != '-' {
				return fmt.Errorf("label %q contains invalid character %q", label, c)
			}
		}
	}
	return nil
}

// isASCIIAlnum reports whether c is an ASCII letter or digit.
// Hostnames are restricted to ASCII per RFC 1123.
func isASCIIAlnum(c rune) bool {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
}
