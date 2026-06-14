package distribution

import (
	"database/sql"
	"fmt"
	"log/slog"
	"net/http"

	"golang.org/x/crypto/bcrypt"

	"github.com/distribution/distribution/v3/registry/auth"
	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/oci"
)

func init() {
	if err := auth.Register("quaydb", auth.InitFunc(newAccessController)); err != nil {
		slog.Error("failed to register quaydb auth", "err", err)
	}
}

type accessController struct {
	queries *daldb.Queries
	realm   string
}

var _ auth.AccessController = &accessController{}
var _ oci.Authenticator = &accessController{}

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

func (ac *accessController) authenticateUser(r *http.Request) (string, bool) {
	username, password, ok := r.BasicAuth()
	if !ok {
		return "", false
	}

	var hashToCompare []byte

	user, err := ac.queries.GetUserByUsername(r.Context(), username)
	if err != nil || !user.Enabled || !user.PasswordHash.Valid {
		hashToCompare = dummyHash
	} else {
		hashToCompare = []byte(user.PasswordHash.String)
	}

	if bcrypt.CompareHashAndPassword(hashToCompare, []byte(password)) != nil ||
		err != nil || !user.Enabled || !user.PasswordHash.Valid {
		slog.Debug("authentication failed", "username", username)
		return username, false
	}

	return username, true
}

func (ac *accessController) Authorized(req *http.Request, access ...auth.Access) (*auth.Grant, error) {
	username, ok := ac.authenticateUser(req)
	if !ok && username == "" {
		return nil, &challenge{
			realm: ac.realm,
			err:   auth.ErrInvalidCredential,
		}
	}
	if !ok {
		return nil, &challenge{
			realm: ac.realm,
			err:   auth.ErrAuthenticationFailure,
		}
	}

	return &auth.Grant{User: auth.UserInfo{Name: username}}, nil
}

func (ac *accessController) Authenticate(r *http.Request, _ ...oci.Access) (*oci.Grant, error) {
	username, ok := ac.authenticateUser(r)
	if !ok {
		return nil, &challenge{
			realm: ac.realm,
			err:   oci.ErrUnauthorized,
		}
	}

	return &oci.Grant{User: oci.User{Name: username}}, nil
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
