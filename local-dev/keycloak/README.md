# Keycloak OIDC for Quay Local Development

This directory contains configuration for running Keycloak as an OIDC authentication provider for Quay during local development.

## Quick Start

1. **Start Keycloak container**:
   ```bash
   docker-compose up -d keycloak
   ```

2. **Enable OIDC in Quay config**:
   ```bash
   make enable-oidc
   ```

3. **Restart Quay to apply changes**:
   ```bash
   docker-compose restart quay
   ```

4. **Access Quay and test login**:
   - Navigate to http://localhost:8080
   - Click "Sign in with Keycloak"
   - Login with any test user (see below)

## Files

- **quay-realm-export.json**: Keycloak realm configuration with client and test users
- **keycloak-config.yaml**: OIDC provider config for merging into Quay's config.yaml
- **init-keycloak.sh**: Verification script to check Keycloak setup (optional)
- **README.md**: This file

## Sample Users

All users have the password: `password`

| Username   | Email                  | Description           |
|-----------|------------------------|----------------------|
| admin     | admin@example.com      | Admin user           |
| user1     | user1@example.com      | Regular user         |
| quayuser  | quayuser@example.com   | Quay-specific user   |
| testuser  | testuser@example.com   | Test user            |

## Testing OIDC Login

1. **Start the environment**:
   ```bash
   make local-dev-up
   docker-compose up -d keycloak
   ```

2. **Wait for Keycloak to be ready** (health check passes in ~30-60 seconds):
   ```bash
   docker-compose ps keycloak
   ```
   Look for "healthy" status.

3. **Enable OIDC**:
   ```bash
   make enable-oidc
   docker-compose restart quay
   ```

4. **Test the login flow**:
   - Open http://localhost:8080 in your browser
   - Click "Sign in with Keycloak"
   - You'll be redirected to Keycloak at http://localhost:8081
   - Enter username: `quayuser` and password: `password`
   - Click "Sign In"
   - You should be redirected back to Quay and logged in

## Networking

Keycloak runs on port 8081 and is accessible:
- **From your browser**: http://localhost:8081
- **From Quay container**: http://host.containers.internal:8081

This dual-access pattern is required for OIDC:
- Browser needs to access Keycloak for the login UI
- Quay needs to access Keycloak for token validation

The `host.containers.internal` hostname is automatically available in Docker/Podman containers to reach services on the host.

## OIDC Configuration Details

The `make enable-oidc` command merges the following into Quay's config:

```yaml
SOMEOIDC_LOGIN_CONFIG:
  SERVICE_NAME: "Keycloak"
  OIDC_SERVER: "http://host.containers.internal:8081/realms/quay/"
  CLIENT_ID: "quay-ui"
  LOGIN_SCOPES: ["openid", "profile", "email"]
  DEBUGGING: true
  USE_PKCE: true
  PKCE_METHOD: "S256"
  PUBLIC_CLIENT: true
```

### Key Settings Explained

- **SERVICE_NAME**: Display name shown in Quay UI ("Sign in with Keycloak")
- **OIDC_SERVER**: Keycloak realm URL (must include trailing slash)
- **CLIENT_ID**: OAuth client identifier (matches realm export)
- **LOGIN_SCOPES**: OIDC scopes requested during login
  - `openid`: Required for OIDC (provides ID token)
  - `profile`: Provides name and username claims
  - `email`: Provides email claim
- **DEBUGGING**: Enable verbose OIDC logging in Quay
- **USE_PKCE**: Enable Proof Key for Code Exchange (OAuth 2.1 best practice)
- **PKCE_METHOD**: Use SHA-256 hashing for PKCE (most secure)
- **PUBLIC_CLIENT**: Client doesn't use a secret (appropriate for web apps)

## Verification

### Check Keycloak Health

```bash
# Check container status
docker-compose ps keycloak

# Check realm endpoint (verifies Keycloak is responding)
curl -sf http://localhost:8081/realms/quay
```

### Verify OIDC Discovery

```bash
# Get OIDC configuration
curl -s http://localhost:8081/realms/quay/.well-known/openid-configuration | jq

# Should show authorization_endpoint, token_endpoint, etc.
```

### Verify Realm Import

```bash
# Get admin token
KC_TOKEN=$(curl -s -X POST \
  -d 'client_id=admin-cli' \
  -d 'username=admin' \
  -d 'password=admin' \
  -d 'grant_type=password' \
  http://localhost:8081/realms/master/protocol/openid-connect/token | jq -r .access_token)

# Check realm exists
curl -s -H "Authorization: Bearer $KC_TOKEN" \
  http://localhost:8081/admin/realms/quay | jq -r '.realm'
# Expected output: "quay"

# Check client configuration
curl -s -H "Authorization: Bearer $KC_TOKEN" \
  'http://localhost:8081/admin/realms/quay/clients?clientId=quay-ui' | jq

# Check users
curl -s -H "Authorization: Bearer $KC_TOKEN" \
  http://localhost:8081/admin/realms/quay/users | jq -r '.[].username'
# Expected output: admin, user1, quayuser, testuser
```

### Verify PKCE Configuration

When you initiate login, check that the authorization URL includes PKCE parameters:

```bash
# The auth URL should contain:
# - code_challenge=<base64url-encoded-string>
# - code_challenge_method=S256
```

You can see this in:
- Browser developer tools (Network tab)
- Quay application logs (with DEBUGGING: true)

## Troubleshooting

### Keycloak container fails to start

**Symptom**: Container exits immediately or shows error logs

**Solutions**:
1. Check port 8081 is not in use:
   ```bash
   lsof -i :8081
   ```
   Kill any conflicting process or change the port in docker-compose.yaml

2. Check logs for specific errors:
   ```bash
   docker-compose logs keycloak
   ```

### Keycloak takes too long to start

**Symptom**: Health check never passes, container stuck in "starting"

**Solutions**:
1. Wait up to 60 seconds - first startup imports the realm
2. Check available resources (RAM, CPU)
3. Check logs for errors:
   ```bash
   docker-compose logs -f keycloak
   ```

### "Keycloak container not running" warning

**Symptom**: `make enable-oidc` shows warning

**Solution**: This is just a warning. Start Keycloak:
```bash
docker-compose up -d keycloak
```

### Quay can't reach Keycloak

**Symptom**: Login fails with connection error, logs show "Connection refused"

**Solutions**:
1. Verify host.containers.internal is available:
   ```bash
   docker exec quay-quay curl -sf http://host.containers.internal:8081/health/ready
   ```

2. If that fails, try alternative hostnames:
   ```bash
   # Docker Desktop
   docker exec quay-quay curl -sf http://host.docker.internal:8081/health/ready

   # Docker bridge IP (Linux)
   docker exec quay-quay curl -sf http://172.17.0.1:8081/health/ready
   ```

3. Update `keycloak-config.yaml` with working hostname and re-run `make enable-oidc`

### Login redirect fails

**Symptom**: After Keycloak login, redirect to Quay fails or shows error

**Solutions**:
1. Check redirect URIs in realm export include:
   - `http://localhost:8080/*`
   - `http://localhost:8080/oauth2/someoidc/callback*`

2. Verify CORS is configured (webOrigins: `["+"]`)

3. Check Quay logs for OAuth errors:
   ```bash
   docker-compose logs quay | grep -i oidc
   ```

### "Sign in with Keycloak" button doesn't appear

**Symptom**: Quay UI doesn't show OIDC login option

**Solutions**:
1. Verify config was merged:
   ```bash
   grep -A 10 "SOMEOIDC_LOGIN_CONFIG" local-dev/stack/config.yaml
   ```

2. Ensure Quay was restarted after config change:
   ```bash
   docker-compose restart quay
   ```

3. Check Quay external login API:
   ```bash
   curl -s http://localhost:8080/api/v1/externallogin | jq
   ```
   Should show Keycloak provider.

## Advanced Configuration

### Disable PKCE

If you need to test without PKCE (not recommended):

Edit `local-dev/keycloak/keycloak-config.yaml`:
```yaml
SOMEOIDC_LOGIN_CONFIG:
  # ... other settings ...
  USE_PKCE: false
  # Remove PKCE_METHOD and PUBLIC_CLIENT
```

Also update realm export to remove PKCE enforcement:
```json
"attributes": {
  "pkce.code.challenge.method": ""
}
```

### Use Confidential Client

To use a confidential client (with client secret):

1. Edit realm export:
   ```json
   "publicClient": false,
   "secret": "your-secret-here"
   ```

2. Edit keycloak-config.yaml:
   ```yaml
   SOMEOIDC_LOGIN_CONFIG:
     CLIENT_SECRET: "your-secret-here"
     PUBLIC_CLIENT: false
   ```

3. Re-import and restart:
   ```bash
   docker-compose down keycloak
   docker-compose up -d keycloak
   make enable-oidc
   docker-compose restart quay
   ```

### Add Additional Users

**Option 1: Edit realm export (recommended)**

Add to `quay-realm-export.json` users array:
```json
{
  "username": "newuser",
  "enabled": true,
  "emailVerified": true,
  "email": "newuser@example.com",
  "firstName": "New",
  "lastName": "User",
  "credentials": [
    {
      "type": "password",
      "value": "password",
      "temporary": false
    }
  ]
}
```

Then restart Keycloak to re-import.

**Option 2: Keycloak Admin Console**

1. Navigate to http://localhost:8081/admin
2. Login with admin/admin
3. Select "quay" realm
4. Click "Users" → "Add user"
5. Fill in details and click "Create"
6. Go to "Credentials" tab and set password

**Option 3: Admin API**

```bash
# Get admin token
KC_TOKEN=$(curl -s -X POST \
  -d 'client_id=admin-cli' \
  -d 'username=admin' \
  -d 'password=admin' \
  -d 'grant_type=password' \
  http://localhost:8081/realms/master/protocol/openid-connect/token | jq -r .access_token)

# Create user
curl -X POST \
  -H "Authorization: Bearer $KC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "enabled": true,
    "emailVerified": true,
    "email": "newuser@example.com",
    "firstName": "New",
    "lastName": "User"
  }' \
  http://localhost:8081/admin/realms/quay/users

# Set password (get user ID first)
USER_ID=$(curl -s -H "Authorization: Bearer $KC_TOKEN" \
  'http://localhost:8081/admin/realms/quay/users?username=newuser' | jq -r '.[0].id')

curl -X PUT \
  -H "Authorization: Bearer $KC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "password",
    "value": "password",
    "temporary": false
  }' \
  http://localhost:8081/admin/realms/quay/users/$USER_ID/reset-password
```

## Comparison: LDAP vs OIDC Setup

| Aspect | LDAP | OIDC/Keycloak |
|--------|------|---------------|
| **Container** | 389 Directory Server | Keycloak |
| **Port** | 3389/6636 | 8081 |
| **Make Target** | `make enable-ldap` | `make enable-oidc` |
| **Auth Type** | Sets `AUTHENTICATION_TYPE: LDAP` | Additive provider (SOMEOIDC_LOGIN_CONFIG) |
| **Exclusivity** | Exclusive (disables other auth) | Coexists with database/other providers |
| **Init Method** | Shell script + LDIF import | Built-in `--import-realm` |
| **User Storage** | LDIF file | JSON realm export |
| **Health Check** | `ldapsearch` command | HTTP `/health/ready` |
| **Discovery** | Manual config | OIDC `.well-known` discovery |
| **Use Case** | Enterprise directory integration | Modern OAuth/OIDC flows, SSO |

## Reset Instructions

To completely reset and start fresh:

```bash
# Stop and remove Keycloak
docker-compose down keycloak

# Restore original config
cp local-dev/stack/config.yaml.backup local-dev/stack/config.yaml

# Restart Quay
docker-compose restart quay

# Start fresh Keycloak
docker-compose up -d keycloak

# Re-enable OIDC
make enable-oidc
docker-compose restart quay
```

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OIDC Specification](https://openid.net/connect/)
- [OAuth 2.1 Draft](https://oauth.net/2.1/)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [Quay OIDC Implementation](../../oauth/oidc.py)

## Keycloak Admin Console

Access the Keycloak admin console to manage the realm:

- **URL**: http://localhost:8081/admin
- **Username**: admin
- **Password**: admin
- **Realm**: quay

From here you can:
- View/edit users
- Configure client settings
- View authentication logs
- Export realm configuration
- Test OIDC flows
