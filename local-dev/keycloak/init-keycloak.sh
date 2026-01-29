#!/bin/bash
# Keycloak verification script for Quay local development
# This script validates that Keycloak is properly configured with the quay realm
#
# Usage: ./init-keycloak.sh
#
# This script is optional - the realm auto-imports during Keycloak startup.
# Use this for troubleshooting or verification purposes.

set -e

KEYCLOAK_URL="http://localhost:8081"
REALM_NAME="quay"
CLIENT_ID="quay-ui"
ADMIN_USER="admin"
ADMIN_PASSWORD="admin"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Keycloak Verification Script"
echo "========================================="
echo ""

# Function to print success message
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error message
error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to print info message
info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if Keycloak is running
echo "Checking Keycloak status..."
if ! curl -sf "${KEYCLOAK_URL}/realms/quay" > /dev/null 2>&1; then
    error "Keycloak is not ready!"
    info "Start Keycloak with: docker-compose up -d keycloak"
    info "Wait for Keycloak to start (may take up to 60 seconds)"
    exit 1
fi
success "Keycloak is ready!"
echo ""

# Check OIDC discovery endpoint
echo "Checking OIDC discovery endpoint..."
DISCOVERY_URL="${KEYCLOAK_URL}/realms/${REALM_NAME}/.well-known/openid-configuration"
if ! curl -sf "$DISCOVERY_URL" > /dev/null 2>&1; then
    error "OIDC discovery endpoint not accessible!"
    info "URL: $DISCOVERY_URL"
    exit 1
fi
success "OIDC discovery endpoint is accessible"

# Verify issuer
ISSUER=$(curl -s "$DISCOVERY_URL" | jq -r '.issuer')
info "Issuer: $ISSUER"
echo ""

# Get admin token
echo "Getting admin token..."
TOKEN_RESPONSE=$(curl -s -X POST \
    -d "client_id=admin-cli" \
    -d "username=${ADMIN_USER}" \
    -d "password=${ADMIN_PASSWORD}" \
    -d "grant_type=password" \
    "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token")

ADMIN_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
    error "Failed to get admin token!"
    info "Response: $TOKEN_RESPONSE"
    exit 1
fi
success "Admin token obtained"
echo ""

# Check realm exists
echo "Checking '${REALM_NAME}' realm..."
REALM_INFO=$(curl -s -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}")

REALM_EXISTS=$(echo "$REALM_INFO" | jq -r '.realm')
if [ "$REALM_EXISTS" != "$REALM_NAME" ]; then
    error "Realm '${REALM_NAME}' does not exist!"
    info "Expected: ${REALM_NAME}"
    info "Got: ${REALM_EXISTS}"
    exit 1
fi
success "Realm '${REALM_NAME}' exists"

# Check SSL requirement
SSL_REQUIRED=$(echo "$REALM_INFO" | jq -r '.sslRequired')
info "SSL Required: $SSL_REQUIRED"
echo ""

# Check client exists
echo "Checking '${CLIENT_ID}' client..."
CLIENT_INFO=$(curl -s -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/clients?clientId=${CLIENT_ID}")

CLIENT_UUID=$(echo "$CLIENT_INFO" | jq -r '.[0].id')
if [ "$CLIENT_UUID" == "null" ] || [ -z "$CLIENT_UUID" ]; then
    error "Client '${CLIENT_ID}' does not exist!"
    exit 1
fi
success "Client '${CLIENT_ID}' exists (ID: ${CLIENT_UUID})"

# Check client is public
IS_PUBLIC=$(echo "$CLIENT_INFO" | jq -r '.[0].publicClient')
if [ "$IS_PUBLIC" != "true" ]; then
    error "Client is not public!"
    info "Expected: true, Got: $IS_PUBLIC"
else
    success "Client is public (no secret required)"
fi

# Check PKCE configuration
PKCE_METHOD=$(echo "$CLIENT_INFO" | jq -r '.[0].attributes["pkce.code.challenge.method"]')
if [ "$PKCE_METHOD" == "S256" ]; then
    success "PKCE is configured (method: S256)"
else
    error "PKCE not properly configured!"
    info "Expected: S256, Got: $PKCE_METHOD"
fi

# Check redirect URIs
REDIRECT_URIS=$(echo "$CLIENT_INFO" | jq -r '.[0].redirectUris[]')
info "Redirect URIs:"
echo "$REDIRECT_URIS" | while read -r uri; do
    echo "  - $uri"
done
echo ""

# Check users
echo "Checking test users..."
USERS=$(curl -s -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}/users")

USER_COUNT=$(echo "$USERS" | jq '. | length')
if [ "$USER_COUNT" -lt 1 ]; then
    error "No users found in realm!"
    exit 1
fi
success "Found $USER_COUNT user(s)"

# List usernames
USERNAMES=$(echo "$USERS" | jq -r '.[].username' | tr '\n' ' ')
info "Users: $USERNAMES"
echo ""

# Test user login (password grant)
echo "Testing user login (quayuser)..."
USER_LOGIN_RESPONSE=$(curl -s -X POST \
    -d "client_id=${CLIENT_ID}" \
    -d "username=quayuser" \
    -d "password=password" \
    -d "grant_type=password" \
    "${KEYCLOAK_URL}/realms/${REALM_NAME}/protocol/openid-connect/token")

USER_TOKEN=$(echo "$USER_LOGIN_RESPONSE" | jq -r '.access_token')
if [ "$USER_TOKEN" == "null" ] || [ -z "$USER_TOKEN" ]; then
    error "User login failed!"
    info "Response: $USER_LOGIN_RESPONSE"
else
    success "User login successful"

    # Decode token to show claims
    TOKEN_CLAIMS=$(echo "$USER_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq -r '{preferred_username, email, name}')
    info "Token claims:"
    echo "$TOKEN_CLAIMS" | jq .
fi
echo ""

# Summary
echo "========================================="
success "All Keycloak checks passed!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Enable OIDC: make enable-oidc"
echo "  2. Restart Quay: docker-compose restart quay"
echo "  3. Test login: http://localhost:8080"
echo ""
