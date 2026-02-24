package config

import (
	"fmt"
	"regexp"

	"gopkg.in/yaml.v3"
)

// durationPattern matches Quay duration strings like "2w", "1d", "0s".
var durationPattern = regexp.MustCompile(`^\d+([wmdhs])$`)

// Storage holds distributed storage configuration.
type Storage struct {
	DistributedStorageConfig      StorageEntries `yaml:"DISTRIBUTED_STORAGE_CONFIG"`
	DistributedStoragePreference  []string       `yaml:"DISTRIBUTED_STORAGE_PREFERENCE"`
	DistributedStorageDefaultLocs []string       `yaml:"DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS"`
	DefaultTagExpiration          string         `yaml:"DEFAULT_TAG_EXPIRATION"`
	TagExpirationOptions          []string       `yaml:"TAG_EXPIRATION_OPTIONS"`
}

// StorageEntries maps storage IDs to their configuration.
type StorageEntries map[string]StorageEntry

// StorageEntry represents a single storage engine configuration.
// In YAML, each entry is a two-element sequence: [DriverName, {params}].
type StorageEntry struct {
	Driver string
	Params map[string]any
}

// UnmarshalYAML handles the Quay-specific tuple format:
//
//	some_id:
//	  - LocalStorage
//	  - storage_path: /data
func (s *StorageEntries) UnmarshalYAML(value *yaml.Node) error {
	if value.Kind != yaml.MappingNode {
		return fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG: expected mapping, got %v", value.Kind)
	}

	*s = make(StorageEntries, len(value.Content)/2)

	for i := 0; i < len(value.Content); i += 2 {
		keyNode := value.Content[i]
		valNode := value.Content[i+1]

		id := keyNode.Value

		if valNode.Kind != yaml.SequenceNode || len(valNode.Content) < 1 {
			return fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG.%s: expected [driver, {params}] sequence", id)
		}
		if len(valNode.Content) > 2 {
			return fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG.%s: expected at most 2 elements [driver, {params}], got %d", id, len(valNode.Content))
		}

		var entry StorageEntry

		if err := valNode.Content[0].Decode(&entry.Driver); err != nil {
			return fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG.%s: decoding driver: %w", id, err)
		}

		if len(valNode.Content) >= 2 {
			entry.Params = make(map[string]any)
			if err := valNode.Content[1].Decode(&entry.Params); err != nil {
				return fmt.Errorf("DISTRIBUTED_STORAGE_CONFIG.%s: decoding params: %w", id, err)
			}
		}

		(*s)[id] = entry
	}

	return nil
}

// validateStorage cross-references storage preferences against defined entries.
func validateStorage(cfg *Config, _ ValidateOptions) []ValidationError {
	var errs []ValidationError

	for _, pref := range cfg.DistributedStoragePreference {
		if _, ok := cfg.DistributedStorageConfig[pref]; !ok {
			errs = append(errs, ValidationError{
				Field: "DISTRIBUTED_STORAGE_PREFERENCE", Severity: SeverityError,
				Message: fmt.Sprintf("%q is not defined in DISTRIBUTED_STORAGE_CONFIG", pref),
			})
		}
	}

	for _, loc := range cfg.DistributedStorageDefaultLocs {
		if _, ok := cfg.DistributedStorageConfig[loc]; !ok {
			errs = append(errs, ValidationError{
				Field: "DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS", Severity: SeverityError,
				Message: fmt.Sprintf("%q is not defined in DISTRIBUTED_STORAGE_CONFIG", loc),
			})
		}
	}

	// Validate DEFAULT_TAG_EXPIRATION format.
	if !durationPattern.MatchString(cfg.DefaultTagExpiration) {
		errs = append(errs, ValidationError{
			Field: "DEFAULT_TAG_EXPIRATION", Severity: SeverityError,
			Message: fmt.Sprintf("%q does not match duration pattern (e.g. 2w, 1d, 0s)", cfg.DefaultTagExpiration),
		})
	}

	// Validate each TAG_EXPIRATION_OPTIONS item.
	for _, opt := range cfg.TagExpirationOptions {
		if !durationPattern.MatchString(opt) {
			errs = append(errs, ValidationError{
				Field: "TAG_EXPIRATION_OPTIONS", Severity: SeverityError,
				Message: fmt.Sprintf("%q does not match duration pattern (e.g. 2w, 1d, 0s)", opt),
			})
		}
	}

	// Cross-reference: DEFAULT_TAG_EXPIRATION must be in TAG_EXPIRATION_OPTIONS.
	if len(cfg.TagExpirationOptions) > 0 {
		found := false
		for _, opt := range cfg.TagExpirationOptions {
			if opt == cfg.DefaultTagExpiration {
				found = true
				break
			}
		}
		if !found {
			errs = append(errs, ValidationError{
				Field: "DEFAULT_TAG_EXPIRATION", Severity: SeverityWarning,
				Message: fmt.Sprintf("%q is not in TAG_EXPIRATION_OPTIONS", cfg.DefaultTagExpiration),
			})
		}
	}

	return errs
}
