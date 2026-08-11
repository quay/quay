#!/bin/bash
# Initialize 389 Directory Server with backend and LDIF import
# This script runs inside the container after 389 DS starts
#
# All authenticated operations use LDAPI (Unix socket) with root autobind
# to avoid dependency on the Directory Manager password.

set -e

LDAPI_URI="ldapi://%2Fdata%2Frun%2Fslapd-localhost.socket"
LDAP_URI="ldap://localhost:3389"
DM_DN="cn=Directory Manager"
DM_PW="${DS_DM_PASSWORD:-admin}"

echo "Waiting for 389 DS to start..."
timeout=60
while [ $timeout -gt 0 ]; do
    if ldapsearch -x -H "${LDAP_URI}" -b "" -s base &>/dev/null; then
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
#
# Attribute and objectClass MUST be added (LDAPI EXTERNAL). A previous bug left
# LDAPI_URI unset, so schema install was a no-op and ldapadd failed with:
#   unknown object class "quayUser"
echo "Adding custom schema for Quay group membership queries..."
ldapmodify -H "${LDAPI_URI}" -Y EXTERNAL 2>&1 <<'SCHEMA_EOF' | grep -v "^SASL" || true
dn: cn=schema
changetype: modify
add: attributeTypes
attributeTypes: ( 1.3.6.1.4.1.99999.1 NAME 'quayMemberOf' DESC 'Quay group membership reference' EQUALITY distinguishedNameMatch SYNTAX 1.3.6.1.4.1.1466.115.121.1.12 )
-
add: objectClasses
objectClasses: ( 1.3.6.1.4.1.99999.2 NAME 'quayUser' DESC 'Quay user auxiliary class' SUP top AUXILIARY MAY ( quayMemberOf ) )
SCHEMA_EOF

if ! ldapsearch -x -H "${LDAP_URI}" -D "${DM_DN}" -w "${DM_PW}" \
    -b "cn=schema" -s base objectClasses 2>/dev/null | grep -q "NAME 'quayUser'"; then
    echo "ERROR: quayUser objectClass missing after schema modify"
    exit 1
fi
echo "quayUser schema installed"

# Import LDIF once Playwright LDAP users are present.
if ldapsearch -x -H "${LDAP_URI}" -D "${DM_DN}" -w "${DM_PW}" \
    -b "uid=admin_ldap,ou=users,dc=example,dc=org" -s base &>/dev/null; then
    echo "LDAP test users already present, skipping LDIF import"
else
    echo "Importing LDIF from /data/ldif/base.ldif..."
    # Prefer LDAPI (matches redhat-3.17/master). -c continues past "Already exists".
    ldapadd -c -H "${LDAPI_URI}" -Y EXTERNAL -f /data/ldif/base.ldif 2>&1 | grep -v "^SASL" || true
    if ! ldapsearch -x -H "${LDAP_URI}" -D "${DM_DN}" -w "${DM_PW}" \
        -b "uid=admin_ldap,ou=users,dc=example,dc=org" -s base &>/dev/null; then
        echo "ERROR: uid=admin_ldap was not imported (schema/LDIF failure)"
        exit 1
    fi
    echo "LDIF imported successfully!"
fi

echo "389 DS initialization complete!"
