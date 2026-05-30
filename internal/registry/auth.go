// Package registry provides authentication and TLS for the quay OCI registry.
package registry

import (
	"database/sql"
	"fmt"
	"net/http"

	"golang.org/x/crypto/bcrypt"

	"github.com/distribution/distribution/v3/registry/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/sirupsen/logrus"
)

func init() {
	if err := auth.Register("quaydb", auth.InitFunc(newAccessController)); err != nil {
		logrus.Errorf("failed to register quaydb auth: %v", err)
	}
}

type accessController struct {
	queries *daldb.Queries
	realm   string
}

var _ auth.AccessController = &accessController{}

func newAccessController(options map[string]interface{}) (auth.AccessController, error) {
	realm, ok := options["realm"].(string)
	if !ok || realm == "" {
		return nil, fmt.Errorf(`"realm" must be set for quaydb access controller`)
	}

	db, ok := options["db"].(*sql.DB)
	if !ok || db == nil {
		return nil, fmt.Errorf(`"db" must be set to *sql.DB for quaydb access controller`)
	}

	return &accessController{
		queries: daldb.New(db),
		realm:   realm,
	}, nil
}

// dummyHash is a valid bcrypt hash used when the user is not found, so that
// bcrypt.CompareHashAndPassword always runs and timing is constant regardless
// of whether the username exists.
var dummyHash = []byte("$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy")

func (ac *accessController) Authorized(req *http.Request, access ...auth.Access) (*auth.Grant, error) {
	username, password, ok := req.BasicAuth()
	if !ok {
		return nil, &challenge{
			realm: ac.realm,
			err:   auth.ErrInvalidCredential,
		}
	}

	var (
		hashToCompare []byte
		authenticated bool
	)

	user, err := ac.queries.GetUserByUsername(req.Context(), username)
	if err != nil || !user.Enabled || !user.PasswordHash.Valid {
		hashToCompare = dummyHash
	} else {
		hashToCompare = []byte(user.PasswordHash.String)
	}

	if bcrypt.CompareHashAndPassword(hashToCompare, []byte(password)) == nil &&
		err == nil && user.Enabled && user.PasswordHash.Valid {
		authenticated = true
	}

	if !authenticated {
		logrus.WithField("username", username).Debug("authentication failed")
		return nil, &challenge{
			realm: ac.realm,
			err:   auth.ErrAuthenticationFailure,
		}
	}

	return &auth.Grant{User: auth.UserInfo{Name: username}}, nil
}

// challenge implements auth.Challenge for Basic auth 401 responses.
type challenge struct {
	realm string
	err   error
}

var _ auth.Challenge = challenge{}

func (ch challenge) SetHeaders(_ *http.Request, w http.ResponseWriter) {
	w.Header().Set("WWW-Authenticate", fmt.Sprintf("Basic realm=%q", ch.realm))
}

func (ch challenge) Error() string {
	return fmt.Sprintf("basic authentication challenge for realm %q: %s", ch.realm, ch.err)
}
