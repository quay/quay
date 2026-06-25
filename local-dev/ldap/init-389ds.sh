#!/bin/bash
# Initialize 389 Directory Server with backend and LDIF import
# This script runs inside the container after 389 DS starts
#
# All authenticated operations use LDAPI (Unix socket) with root autobind
# to avoid dependency on the Directory Manager password.

set -e

LDAPI_URI="ldapi://%2Fdata%2Frun%2Fslapd-localhost.socket"

echo "Waiting for 389 DS to start..."
timeout=30
while [ $timeout -gt 0 ]; do
    if ldapsearch -x -H ldap://localhost:3389 -b "" -s base &>/dev/null; then
        echo "389 DS is ready!"
        break
    fi
    sleep 1
    timeout=$((timeout - 1))
done

if [ $timeout -eq 0 ]; then
    echo "ERROR: 389 DS failed to start"
    exit 1
fi

# Check if backend already exists
if dsconf localhost backend suffix list | grep -q "dc=example,dc=org"; then
    echo "Backend already exists, skipping creation"
else
    echo "Creating backend for dc=example,dc=org..."
    dsconf localhost backend create --suffix "dc=example,dc=org" --be-name userroot
fi

# Add a custom user-modifiable schema attribute for LDAP group membership queries.
# The built-in memberOf attribute is NO-USER-MODIFICATION (server-managed by the
# MemberOf plugin), so it cannot be set in base.ldif. quayMemberOf is a regular
# DN-syntax attribute we can set freely. Quay reads LDAP_MEMBEROF_ATTR from
# ldap-config.yaml to know which attribute to query.
echo "Adding custom schema for Quay group membership queries..."
ldapmodify -H "$LDAPI_URI" -Y EXTERNAL 2>&1 << 'SCHEMA_EOF' | grep -v "^SASL" || true
dn: cn=schema
changetype: modify
add: attributeTypes
attributeTypes: ( 1.3.6.1.4.1.99999.1 NAME 'quayMemberOf' DESC 'Quay group membership reference' EQUALITY distinguishedNameMatch SYNTAX 1.3.6.1.4.1.1466.115.121.1.12 )
-
add: objectClasses
objectClasses: ( 1.3.6.1.4.1.99999.2 NAME 'quayUser' DESC 'Quay user auxiliary class' SUP top AUXILIARY MAY ( quayMemberOf ) )
SCHEMA_EOF

# Check if base DN exists (anonymous search)
if ldapsearch -x -H ldap://localhost:3389 -b "dc=example,dc=org" -s base &>/dev/null; then
    echo "Base DN already exists, skipping LDIF import"
else
    echo "Importing LDIF from /data/ldif/base.ldif..."
    ldapadd -H "$LDAPI_URI" -Y EXTERNAL -f /data/ldif/base.ldif 2>&1 | grep -v "^SASL" || true
    echo "LDIF imported successfully!"
fi

echo "389 DS initialization complete!"
