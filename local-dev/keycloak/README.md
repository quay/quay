# Keycloak OIDC for Quay Local Development

This directory contains configuration for running Keycloak as an OIDC authentication provider for Quay during local development.

## Quick Start

```bash
# Start everything including Keycloak
make local-dev-up-with-keycloak

# Or manually:
make local-dev-up
docker-compose up -d keycloak
make enable-oidc
docker-compose restart quay
```

## Files

- **quay-realm-export.json**: Keycloak realm configuration with client and test users
- **keycloak-config.yaml**: OIDC provider config for merging into Quay's config.yaml
- **init-keycloak.sh**: Verification script to check Keycloak setup (optional)

## Sample Users

All users have the password: `password`

| Username       | Email                     | Description   |
|----------------|---------------------------|---------------|
| admin_oidc     | admin_oidc@example.com    | Admin user    |
| testuser_oidc  | testuser_oidc@example.com | Regular user  |
| readonly_oidc  | readonly_oidc@example.com | Readonly user |

## Testing OIDC Login

1. Open http://localhost:8080 in your browser
2. Click "Sign in with Keycloak"
3. You'll be redirected to Keycloak at http://localhost:8081
4. Enter username: `quayuser` and password: `password`
5. Click "Sign In"
6. You should be redirected back to Quay and logged in

## Networking

Keycloak runs on port 8081 and is accessible:
- **From your browser**: http://localhost:8081
- **From Quay container**: http://host.containers.internal:8081

## Keycloak Admin Console

- URL: http://localhost:8081/admin
- Username: admin
- Password: admin
