### OIDC + PKCE Validation Guide (Local QA)

This guide validates Quay’s OIDC login both without PKCE and with PKCE enforced.

#### Prereqs
- Podman installed
- Quay repo checked out and local-dev stack available

#### Conventions
- Quay UI: `http://localhost:8080`
- Keycloak: `http://localhost:8081`
- Podman host alias used by Quay container: `http://host.containers.internal:8081`

### 1) Start services
1. Start Quay local-dev (uses podman):
   ```bash
   DOCKER=podman make local-dev-up-static
   ```
2. Start Keycloak (dev mode):
   ```bash
   podman rm -f quay-keycloak >/dev/null 2>&1 || true
   podman run -d --name quay-keycloak \
     -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin \
     -p 8081:8080 quay.io/keycloak/keycloak:latest start-dev
   # Wait until ready
   until curl -sSf http://localhost:8081/realms/master/.well-known/openid-configuration >/dev/null; do sleep 2; done
   ```

### 2) Configure Keycloak realm and client (no PKCE yet)
1. Create realm `quay` and OIDC client `quay-ui` (confidential, standard flow):
   ```bash
   KC_TOKEN=$(curl -s -X POST -d 'client_id=admin-cli' -d 'username=admin' -d 'password=admin' -d 'grant_type=password' \
     http://localhost:8081/realms/master/protocol/openid-connect/token | jq -r .access_token)

   # Realm
   curl -s -X POST -H "Authorization: Bearer $KC_TOKEN" -H 'Content-Type: application/json' \
     http://localhost:8081/admin/realms -d '{"realm":"quay","enabled":true}'

   # Client (allow redirect back to Quay)
   curl -s -X POST -H "Authorization: Bearer $KC_TOKEN" -H 'Content-Type: application/json' \
     http://localhost:8081/admin/realms/quay/clients -d '{
       "clientId":"quay-ui","protocol":"openid-connect","publicClient":false,
       "standardFlowEnabled":true,
       "redirectUris":["http://localhost:8080/oauth2/someoidc/callback*"],
       "webOrigins":["+"]
     }'

   CID=$(curl -s -H "Authorization: Bearer $KC_TOKEN" 'http://localhost:8081/admin/realms/quay/clients?clientId=quay-ui' | jq -r '.[0].id')
   CLIENT_SECRET=$(curl -s -H "Authorization: Bearer $KC_TOKEN" http://localhost:8081/admin/realms/quay/clients/$CID/client-secret | jq -r .value)
   echo "CLIENT_SECRET=$CLIENT_SECRET"
   ```
2. Create a test user:
   ```bash
   # Create user if not present
   curl -s -X POST -H "Authorization: Bearer $KC_TOKEN" -H 'Content-Type: application/json' \
     http://localhost:8081/admin/realms/quay/users -d '{"username":"quayuser","enabled":true,"email":"quayuser@example.com","emailVerified":true}'
   KC_UID=$(curl -s -H "Authorization: Bearer $KC_TOKEN" 'http://localhost:8081/admin/realms/quay/users?username=quayuser' | jq -r '.[0].id')
   curl -s -X PUT -H "Authorization: Bearer $KC_TOKEN" -H 'Content-Type: application/json' \
     http://localhost:8081/admin/realms/quay/users/$KC_UID/reset-password -d '{"type":"password","value":"password","temporary":false}'
   ```

### 3) Configure Quay OIDC provider (no PKCE yet)
Edit `local-dev/stack/config.yaml` and add:
```yaml
SOMEOIDC_LOGIN_CONFIG:
  SERVICE_NAME: "Keycloak"
  OIDC_SERVER: "http://host.containers.internal:8081/realms/quay/"  # note trailing slash
  CLIENT_ID: "quay-ui"
  CLIENT_SECRET: "<CLIENT_SECRET_FROM_ABOVE>"
  LOGIN_SCOPES: ["openid", "profile", "email"]
  DEBUGGING: true
```
Restart Quay:
```bash
podman restart quay-quay
sleep 8
```

Validate baseline (no PKCE):
- Browser: go to `http://localhost:8080`, click “Sign in with Keycloak”, log in as `quayuser` / `password`.
- Expected: Login succeeds; user is logged into Quay.

Optional API check to retrieve auth URL:
```bash
CSRF=$(curl -s -c cookies.txt -b cookies.txt http://localhost:8080/csrf_token | jq -r .csrf_token)
curl -s -b cookies.txt -c cookies.txt -H "X-Requested-With: XMLHttpRequest" -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json" -X POST -d '{"kind":"login"}' \
  http://localhost:8080/api/v1/externallogin/someoidc | jq -r .auth_url
```

### 4) Enforce PKCE on the IdP and confirm failure
1. Require PKCE (S256) on Keycloak client:
   ```bash
   KC_TOKEN=$(curl -s -X POST -d 'client_id=admin-cli' -d 'username=admin' -d 'password=admin' -d 'grant_type=password' \
     http://localhost:8081/realms/master/protocol/openid-connect/token | jq -r .access_token)
   CID=$(curl -s -H "Authorization: Bearer $KC_TOKEN" 'http://localhost:8081/admin/realms/quay/clients?clientId=quay-ui' | jq -r '.[0].id')
   curl -s -H "Authorization: Bearer $KC_TOKEN" http://localhost:8081/admin/realms/quay/clients/$CID > /tmp/client.json
   cat /tmp/client.json | jq '.attributes["pkce.code.challenge.method"]="S256" | .attributes["oauth.pkce.required"]="true"' > /tmp/client-upd.json
   curl -s -X PUT -H "Authorization: Bearer $KC_TOKEN" -H 'Content-Type: application/json' \
     --data-binary @/tmp/client-upd.json http://localhost:8081/admin/realms/quay/clients/$CID
   ```
2. Browser: log out of Quay if logged in, then try “Sign in with Keycloak”.
   - Expected: Login fails with PKCE error on Keycloak (e.g., missing code_challenge_method).

### 5) Enable PKCE in Quay and confirm success
1. Edit `local-dev/stack/config.yaml` to enable PKCE:
   ```yaml
   SOMEOIDC_LOGIN_CONFIG:
     ...
     USE_PKCE: true
     PKCE_METHOD: "S256"
   ```
2. Restart Quay:
   ```bash
   podman restart quay-quay
   sleep 8
   ```
3. Confirm the generated auth URL includes PKCE parameters:
   ```bash
   CSRF=$(curl -s -c cookies.txt -b cookies.txt http://localhost:8080/csrf_token | jq -r .csrf_token)
   AUTHURL=$(curl -s -b cookies.txt -c cookies.txt -H "X-Requested-With: XMLHttpRequest" -H "X-CSRF-Token: $CSRF" \
     -H "Content-Type: application/json" -X POST -d '{"kind":"login"}' http://localhost:8080/api/v1/externallogin/someoidc | jq -r .auth_url)
   echo "$AUTHURL" | grep -E 'code_challenge=.*&code_challenge_method=S256'
   ```
4. Browser: “Sign in with Keycloak” again, log in as `quayuser` / `password`.
   - Expected: Login succeeds (PKCE working end-to-end).

### Expected outcomes summary
- No PKCE: login succeeds.
- IdP PKCE required, Quay PKCE disabled: login fails with PKCE error.
- IdP PKCE required, Quay PKCE enabled: auth URL has `code_challenge` + `code_challenge_method=S256`, login succeeds.

### Troubleshooting notes
- Ensure `OIDC_SERVER` ends with a trailing `/` (required by Quay).
- With podman, Quay must reach Keycloak via `host.containers.internal:8081` (not `localhost`).
- Initial 502s from Quay are normal while warming up; wait ~5–10 seconds.
- Local HTTP causes Keycloak non-secure cookie warnings; safe to ignore during dev.
- Ignore unrelated `securityworker` log errors in Quay during this validation.


