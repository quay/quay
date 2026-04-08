package config

import (
	"reflect"
	"strings"
)

// knownYAMLTags collects all yaml tag names from a struct, recursing into
// embedded structs. It returns a set (map[string]bool) of top-level YAML keys
// that the struct can unmarshal.
func knownYAMLTags(v any) map[string]bool {
	if v == nil {
		return nil
	}
	tags := make(map[string]bool)
	collectTags(reflect.TypeOf(v), tags)
	return tags
}

func collectTags(t reflect.Type, tags map[string]bool) {
	if t == nil {
		return
	}
	if t.Kind() == reflect.Ptr {
		t = t.Elem()
	}
	if t.Kind() != reflect.Struct {
		return
	}

	for i := 0; i < t.NumField(); i++ {
		f := t.Field(i)

		// Recurse into embedded (anonymous) structs.
		if f.Anonymous {
			collectTags(f.Type, tags)
			continue
		}

		tag := f.Tag.Get("yaml")
		if tag == "" || tag == "-" {
			continue
		}

		// Strip options like ",omitempty".
		name := strings.SplitN(tag, ",", 2)[0]
		if name != "" {
			tags[name] = true
		}
	}
}
