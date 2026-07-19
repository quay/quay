package installer

import (
	"fmt"
	"net"
	"strconv"
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

// ValidatePort checks that port is a decimal integer in the range 1–65535.
func ValidatePort(port string) error {
	if port == "" {
		return fmt.Errorf("not a valid number: %q", port)
	}
	for _, c := range port {
		if c < '0' || c > '9' {
			return fmt.Errorf("not a valid number: %q", port)
		}
	}
	n, err := strconv.Atoi(port)
	if err != nil {
		return fmt.Errorf("not a valid number: %q", port)
	}
	if n < 1 || n > 65535 {
		return fmt.Errorf("out of range (1-65535): %d", n)
	}
	return nil
}

// isASCIIAlnum reports whether c is an ASCII letter or digit.
// Hostnames are restricted to ASCII per RFC 1123.
func isASCIIAlnum(c rune) bool {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
}
