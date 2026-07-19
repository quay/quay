package auth

import (
	"fmt"
	"sort"
	"strings"
)

const (
	repositoryResourceType = "repository"
	registryResourceType   = "registry"
	maximumScopeCount      = 100
)

// ParseScopes parses repeated and whitespace-separated scope parameters,
// normalizes repository names, and returns a deterministic de-duplicated list.
func ParseScopes(values []string, service, libraryNamespace string) ([]Scope, error) {
	if service == "" {
		return nil, fmt.Errorf("service must not be empty")
	}
	if libraryNamespace == "" {
		return nil, fmt.Errorf("library namespace must not be empty")
	}

	type scopeKey struct {
		resourceType string
		name         string
	}
	actionsByScope := make(map[scopeKey]map[string]struct{})

	for _, value := range values {
		for _, raw := range strings.Fields(value) {
			scope, err := parseScope(raw, service, libraryNamespace)
			if err != nil {
				return nil, err
			}
			key := scopeKey{resourceType: scope.Type, name: scope.Name}
			actions := actionsByScope[key]
			if actions == nil {
				actions = make(map[string]struct{})
				actionsByScope[key] = actions
				if len(actionsByScope) > maximumScopeCount {
					return nil, fmt.Errorf("too many scopes: maximum is %d", maximumScopeCount)
				}
			}
			for _, action := range scope.Actions {
				actions[action] = struct{}{}
			}
		}
	}

	keys := make([]scopeKey, 0, len(actionsByScope))
	for key := range actionsByScope {
		keys = append(keys, key)
	}
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].resourceType != keys[j].resourceType {
			return keys[i].resourceType < keys[j].resourceType
		}
		return keys[i].name < keys[j].name
	})

	result := make([]Scope, 0, len(keys))
	for _, key := range keys {
		actions := make([]string, 0, len(actionsByScope[key]))
		for action := range actionsByScope[key] {
			actions = append(actions, action)
		}
		sort.Strings(actions)
		result = append(result, Scope{Type: key.resourceType, Name: key.name, Actions: actions})
	}
	return result, nil
}

func parseScope(raw, service, libraryNamespace string) (Scope, error) {
	firstColon := strings.IndexByte(raw, ':')
	lastColon := strings.LastIndexByte(raw, ':')
	if firstColon <= 0 || lastColon <= firstColon+1 || lastColon == len(raw)-1 {
		return Scope{}, fmt.Errorf("invalid scope %q", raw)
	}

	resourceType := raw[:firstColon]
	name := raw[firstColon+1 : lastColon]
	actionList := raw[lastColon+1:]
	if !validToken(resourceType) || name == "" {
		return Scope{}, fmt.Errorf("invalid scope %q", raw)
	}

	switch resourceType {
	case repositoryResourceType:
		name = strings.TrimPrefix(name, service+"/")
		if !strings.Contains(name, "/") {
			name = libraryNamespace + "/" + name
		}
		if !validRepositoryName(name) {
			return Scope{}, fmt.Errorf("invalid repository scope name %q", name)
		}
	case registryResourceType:
		if !validToken(name) {
			return Scope{}, fmt.Errorf("invalid registry scope name %q", name)
		}
	default:
		return Scope{}, fmt.Errorf("unsupported scope resource type %q", resourceType)
	}

	actions := strings.Split(actionList, ",")
	seen := make(map[string]struct{}, len(actions))
	parsedActions := make([]string, 0, len(actions))
	for _, action := range actions {
		if !validScopeAction(action) {
			return Scope{}, fmt.Errorf("invalid scope action %q", action)
		}
		if resourceType == registryResourceType && action != "*" {
			return Scope{}, fmt.Errorf("invalid registry scope action %q", action)
		}
		if _, ok := seen[action]; ok {
			continue
		}
		seen[action] = struct{}{}
		parsedActions = append(parsedActions, action)
	}
	sort.Strings(parsedActions)

	return Scope{Type: resourceType, Name: name, Actions: parsedActions}, nil
}

func validScopeAction(action string) bool {
	switch action {
	case "pull", "push", "delete", "*":
		return true
	default:
		return false
	}
}

func validRepositoryName(name string) bool {
	if strings.Contains(name, ":") {
		return false
	}
	parts := strings.Split(name, "/")
	if len(parts) < 2 {
		return false
	}
	for _, part := range parts {
		if part == "" {
			return false
		}
		for _, r := range part {
			if !isAlphaNumeric(r) && r != '.' && r != '_' && r != '-' {
				return false
			}
		}
	}
	return true
}

func validToken(value string) bool {
	if value == "" {
		return false
	}
	for _, r := range value {
		if !isAlphaNumeric(r) && r != '.' && r != '_' && r != '-' {
			return false
		}
	}
	return true
}

func isAlphaNumeric(r rune) bool {
	return r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9'
}
