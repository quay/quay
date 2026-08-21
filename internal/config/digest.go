package config

import (
	"fmt"

	"gopkg.in/yaml.v3"
)

var supportedHashAlgorithms = map[string]struct{}{
	"sha256": {},
	"sha512": {},
}

// HashAlgorithms is a strictly typed list of digest algorithm identifiers.
type HashAlgorithms []string

// UnmarshalYAML rejects YAML coercion of non-string values into strings.
func (algorithms *HashAlgorithms) UnmarshalYAML(value *yaml.Node) error {
	if value.Kind != yaml.SequenceNode {
		return fmt.Errorf("ALLOWED_HASH_ALGORITHMS: expected a sequence of strings")
	}

	decoded := make(HashAlgorithms, len(value.Content))
	for index, item := range value.Content {
		if item.Kind != yaml.ScalarNode || item.Tag != "!!str" {
			return fmt.Errorf(
				"ALLOWED_HASH_ALGORITHMS: item %d must be a string",
				index,
			)
		}
		decoded[index] = item.Value
	}

	*algorithms = decoded
	return nil
}

// Digest holds client-visible digest algorithm settings. Canonical internal
// storage and deduplication continue to use SHA-256 independently of this list.
type Digest struct {
	AllowedHashAlgorithms HashAlgorithms `yaml:"ALLOWED_HASH_ALGORITHMS"`
}

// validateDigest checks that the configured exact allowlist is non-empty,
// unique, and contains only supported lowercase algorithm identifiers.
func validateDigest(cfg *Config, _ ValidateOptions) []ValidationError {
	if len(cfg.AllowedHashAlgorithms) == 0 {
		return []ValidationError{{
			Field:    fieldAllowedHashAlgorithms,
			Severity: SeverityError,
			Message:  "must contain at least one algorithm",
		}}
	}

	seen := make(map[string]struct{}, len(cfg.AllowedHashAlgorithms))
	var errs []ValidationError
	for _, algorithm := range cfg.AllowedHashAlgorithms {
		if _, duplicate := seen[algorithm]; duplicate {
			errs = append(errs, ValidationError{
				Field:    fieldAllowedHashAlgorithms,
				Severity: SeverityError,
				Message:  fmt.Sprintf("contains duplicate algorithm %q", algorithm),
			})
			continue
		}
		seen[algorithm] = struct{}{}

		if _, supported := supportedHashAlgorithms[algorithm]; !supported {
			errs = append(errs, ValidationError{
				Field:    fieldAllowedHashAlgorithms,
				Severity: SeverityError,
				Message:  fmt.Sprintf("contains unsupported algorithm %q", algorithm),
			})
		}
	}

	return errs
}
