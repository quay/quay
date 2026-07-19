package auth

import (
	"reflect"
	"testing"
)

func TestParseScopesNormalizesAndDeduplicates(t *testing.T) {
	got, err := ParseScopes([]string{
		"repository:registry.example.com:8443/acme/team/image:push,pull,pull",
		"repository:acme/team/image:delete repository:busybox:pull",
		"repository:acme/team/image:push",
	}, "registry.example.com:8443", "library")
	if err != nil {
		t.Fatal(err)
	}
	want := []Scope{
		{Type: "repository", Name: "acme/team/image", Actions: []string{"delete", "pull", "push"}},
		{Type: "repository", Name: "library/busybox", Actions: []string{"pull"}},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("scopes = %#v, want %#v", got, want)
	}
}

func TestParseScopesAcceptsCatalog(t *testing.T) {
	got, err := ParseScopes([]string{"registry:catalog:*"}, "registry.example.com", "library")
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 || got[0].Type != "registry" || got[0].Name != "catalog" {
		t.Fatalf("unexpected scopes: %#v", got)
	}
}

func TestParseScopesRejectsMalformedValues(t *testing.T) {
	tests := []string{
		"repository", "repository::pull", "repository:acme/repo:",
		"repository:acme//repo:pull", "repository:other.example:8443/acme/repo:pull",
		"repository:acme/Repo:pull",
		"repository:acme/repo:scan", "repository:acme/repo:pull,",
		"registry:catalog:pull", "artifact:acme/repo:pull",
	}
	for _, raw := range tests {
		t.Run(raw, func(t *testing.T) {
			if _, err := ParseScopes([]string{raw}, "registry.example.com:8443", "library"); err == nil {
				t.Fatalf("expected %q to fail", raw)
			}
		})
	}
}

func TestParseScopesEmpty(t *testing.T) {
	got, err := ParseScopes(nil, "registry.example.com", "library")
	if err != nil {
		t.Fatal(err)
	}
	if got == nil || len(got) != 0 {
		t.Fatalf("scopes = %#v, want non-nil empty slice", got)
	}
}
