# Robot API Tokens

Quay robot accounts can use two independent credential types:

- **Static robot token** — the credential shown on the robot account page and used with the robot username for registry push and pull operations.
- **Robot API token** — an expiring, scoped credential with the `qro_` prefix used for Quay API operations.

These credentials have separate lifecycles. Creating, revoking, expiring, or rotating one type does not change the other.

## Static token rotation

Regenerating a robot's static token replaces only that push/pull credential:

- The previous static token can no longer be used to request new registry sessions.
- Existing robot API tokens remain valid until they expire or are explicitly revoked.
- Registry bearer tokens issued before rotation may remain valid until their own expiration.

Use the robot API-token lifecycle endpoints to list and revoke API tokens independently. Rotate the static token and revoke API tokens separately when responding to a suspected compromise of all robot credentials.

## Robot API-token lifecycle

Robot API tokens are returned in plaintext only when created. Store the value securely; subsequent list operations return metadata only.

API tokens:

- Require at least one valid API scope.
- Cannot use the direct-login scope.
- Expire after at most 90 days.
- Are bound to one robot account.
- Can be revoked independently without changing the robot's static push/pull token.

Managing API tokens through the lifecycle endpoints requires an authenticated, fresh human session with permission to administer the robot.
