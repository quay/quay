package auth

import (
	"errors"
	"fmt"
	"net/http"
	"sort"
	"strconv"
	"strings"

	distauth "github.com/distribution/distribution/v3/registry/auth"
)

var (
	errTokenRequired     = errors.New("authorization token required")
	errInsufficientScope = errors.New("insufficient scope")
)

// ControllerConfig configures the shared Distribution access controller.
type ControllerConfig struct {
	Realm            string
	Service          string
	LibraryNamespace string
	Verifier         TokenVerifier
}

// Controller validates bearer tokens for Distribution and custom registry
// endpoints. It is immutable after construction and safe for concurrent use.
type Controller struct {
	realm            string
	service          string
	libraryNamespace string
	verifier         TokenVerifier
}

var _ distauth.AccessController = (*Controller)(nil)

// NewController creates a bearer-only access controller.
func NewController(cfg ControllerConfig) (*Controller, error) {
	if cfg.Realm == "" || cfg.Service == "" || cfg.LibraryNamespace == "" || cfg.Verifier == nil {
		return nil, fmt.Errorf("realm, service, library namespace, and verifier are required")
	}
	return &Controller{
		realm:            cfg.Realm,
		service:          cfg.Service,
		libraryNamespace: cfg.LibraryNamespace,
		verifier:         cfg.Verifier,
	}, nil
}

// Authorized verifies the bearer token and checks exact requested resources
// and actions. A granted wildcard action satisfies every requested action.
func (c *Controller) Authorized(req *http.Request, requested ...distauth.Access) (*distauth.Grant, error) {
	challenge := &bearerChallenge{
		realm: c.realm, service: c.service, scopes: challengeScopes(requested), err: errTokenRequired,
	}

	header := strings.TrimSpace(req.Header.Get("Authorization"))
	fields := strings.Fields(header)
	if len(fields) == 0 || !strings.EqualFold(fields[0], "Bearer") {
		return nil, challenge
	}
	if len(fields) != 2 || fields[1] == "" {
		challenge.err = ErrInvalidToken
		return nil, challenge
	}

	claims, err := c.verifier.Verify(fields[1])
	if err != nil {
		challenge.err = ErrInvalidToken
		return nil, challenge
	}

	granted := make(map[distauth.Resource]map[string]struct{}, len(claims.Access))
	resources := make(map[distauth.Resource]struct{}, len(claims.Access))
	for _, item := range claims.Access {
		resource := distauth.Resource{Type: item.Type, Class: item.Class, Name: item.Name}
		actions := granted[resource]
		if actions == nil {
			actions = make(map[string]struct{})
			granted[resource] = actions
		}
		resources[resource] = struct{}{}
		for _, action := range item.Actions {
			actions[action] = struct{}{}
		}
	}

	for _, item := range requested {
		resource := item.Resource
		resource.Name = c.normalizeResourceName(resource.Type, resource.Name)
		actions := granted[resource]
		_, exact := actions[item.Action]
		_, wildcard := actions["*"]
		if !exact && !wildcard {
			challenge.err = errInsufficientScope
			return nil, challenge
		}
	}

	resourceList := make([]distauth.Resource, 0, len(resources))
	for resource := range resources {
		resourceList = append(resourceList, resource)
	}
	sort.Slice(resourceList, func(i, j int) bool {
		if resourceList[i].Type != resourceList[j].Type {
			return resourceList[i].Type < resourceList[j].Type
		}
		if resourceList[i].Name != resourceList[j].Name {
			return resourceList[i].Name < resourceList[j].Name
		}
		return resourceList[i].Class < resourceList[j].Class
	})

	return &distauth.Grant{
		User: distauth.UserInfo{Name: claims.Subject}, Resources: resourceList,
	}, nil
}

func (c *Controller) normalizeResourceName(resourceType, name string) string {
	if resourceType == repositoryResourceType && !strings.Contains(name, "/") {
		return c.libraryNamespace + "/" + name
	}
	return name
}

type bearerChallenge struct {
	realm   string
	service string
	scopes  string
	err     error
}

var _ distauth.Challenge = (*bearerChallenge)(nil)

func (c *bearerChallenge) Error() string { return c.err.Error() }

func (c *bearerChallenge) SetHeaders(_ *http.Request, response http.ResponseWriter) {
	value := "Bearer realm=" + strconv.Quote(c.realm) + ",service=" + strconv.Quote(c.service)
	if c.scopes != "" {
		value += ",scope=" + strconv.Quote(c.scopes)
	}
	switch c.err {
	case ErrInvalidToken:
		value += `,error="invalid_token"`
	case errInsufficientScope:
		value += `,error="insufficient_scope"`
	}
	response.Header().Set("WWW-Authenticate", value)
}

func challengeScopes(requested []distauth.Access) string {
	type resourceKey struct{ resourceType, name string }
	byResource := make(map[resourceKey]map[string]struct{})
	for _, item := range requested {
		key := resourceKey{resourceType: item.Type, name: item.Name}
		actions := byResource[key]
		if actions == nil {
			actions = make(map[string]struct{})
			byResource[key] = actions
		}
		actions[item.Action] = struct{}{}
	}
	keys := make([]resourceKey, 0, len(byResource))
	for key := range byResource {
		keys = append(keys, key)
	}
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].resourceType != keys[j].resourceType {
			return keys[i].resourceType < keys[j].resourceType
		}
		return keys[i].name < keys[j].name
	})
	scopes := make([]string, 0, len(keys))
	for _, key := range keys {
		actions := make([]string, 0, len(byResource[key]))
		for action := range byResource[key] {
			actions = append(actions, action)
		}
		sort.Strings(actions)
		scopes = append(scopes, fmt.Sprintf("%s:%s:%s", key.resourceType, key.name, strings.Join(actions, ",")))
	}
	return strings.Join(scopes, " ")
}
