package shared

import (
	"encoding/json"
	"reflect"
	"testing"

	"gopkg.in/yaml.v3"
)

// TestDistributedStorageArgsSignatureStructTags verifies that the Signature
// field's struct tags are well-formed and parsed correctly by Go's reflect
// package. A malformed validate tag (e.g. `validate: ""` with a space) causes
// the Go tag parser to stop, silently dropping the json and yaml tags.
func TestDistributedStorageArgsSignatureStructTags(t *testing.T) {
	f, ok := reflect.TypeOf(DistributedStorageArgs{}).FieldByName("Signature")
	if !ok {
		t.Fatal("DistributedStorageArgs.Signature field not found")
	}

	tests := []struct {
		tagKey string
		want   string
	}{
		{"json", "signature_version,omitempty"},
		{"yaml", "signature_version,omitempty"},
		{"default", "s3v2"},
		{"validate", ""},
	}

	for _, tt := range tests {
		got := f.Tag.Get(tt.tagKey)
		if got != tt.want {
			t.Errorf("DistributedStorageArgs.Signature tag %q = %q, want %q (struct tag may be malformed)", tt.tagKey, got, tt.want)
		}
	}
}

// TestDistributedStorageArgsSignatureJSONKey verifies that JSON marshalling
// uses "signature_version" (not the Go field name "Signature").
func TestDistributedStorageArgsSignatureJSONKey(t *testing.T) {
	args := DistributedStorageArgs{
		Signature: "s3v4",
	}

	data, err := json.Marshal(args)
	if err != nil {
		t.Fatalf("json.Marshal failed: %v", err)
	}

	var m map[string]interface{}
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatalf("json.Unmarshal failed: %v", err)
	}

	if _, ok := m["Signature"]; ok {
		t.Error("JSON output contains Go field name \"Signature\" instead of \"signature_version\" — struct tag is malformed")
	}
	if val, ok := m["signature_version"]; !ok {
		t.Error("JSON output missing \"signature_version\" key — struct tag is malformed")
	} else if val != "s3v4" {
		t.Errorf("signature_version = %v, want \"s3v4\"", val)
	}
}

// TestDistributedStorageArgsSignatureYAMLKey verifies that YAML marshalling
// uses "signature_version" (not the Go field name "Signature").
func TestDistributedStorageArgsSignatureYAMLKey(t *testing.T) {
	args := DistributedStorageArgs{
		Signature: "s3v4",
	}

	data, err := yaml.Marshal(args)
	if err != nil {
		t.Fatalf("yaml.Marshal failed: %v", err)
	}

	var m map[string]interface{}
	if err := yaml.Unmarshal(data, &m); err != nil {
		t.Fatalf("yaml.Unmarshal failed: %v", err)
	}

	if _, ok := m["Signature"]; ok {
		t.Error("YAML output contains Go field name \"Signature\" instead of \"signature_version\" — struct tag is malformed")
	}
	if val, ok := m["signature_version"]; !ok {
		t.Error("YAML output missing \"signature_version\" key — struct tag is malformed")
	} else if val != "s3v4" {
		t.Errorf("signature_version = %v, want \"s3v4\"", val)
	}
}

// TestDistributedStorageArgsSignatureOmitempty verifies that the Signature
// field is omitted from JSON when empty (omitempty tag is working).
func TestDistributedStorageArgsSignatureOmitempty(t *testing.T) {
	args := DistributedStorageArgs{
		Signature: "",
	}

	data, err := json.Marshal(args)
	if err != nil {
		t.Fatalf("json.Marshal failed: %v", err)
	}

	var m map[string]interface{}
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatalf("json.Unmarshal failed: %v", err)
	}

	if _, ok := m["signature_version"]; ok {
		t.Error("JSON output contains \"signature_version\" for empty value — omitempty not working")
	}
	if _, ok := m["Signature"]; ok {
		t.Error("JSON output contains Go field name \"Signature\" for empty value — struct tag is malformed and omitempty not working")
	}
}
