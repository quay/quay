#!/bin/bash
# Initialize 389 Directory Server with backend and LDIF import
# This script runs inside the container after 389 DS starts

set -e

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

# Enable dynamic plugins (allows plugin changes without restart)
echo "Enabling dynamic plugins..."
dsconf localhost config replace nsslapd-dynamic-plugins=on

# Enable memberOf plugin for team sync support
if dsconf localhost plugin memberof status 2>&1 | grep -q "disabled"; then
    echo "Enabling memberOf plugin..."
    dsconf localhost plugin memberof enable
    echo "memberOf plugin enabled!"
else
    echo "memberOf plugin already enabled"
fi

# Check if backend already exists
if dsconf localhost backend suffix list | grep -q "dc=example,dc=org"; then
    echo "Backend already exists, skipping creation"
else
    echo "Creating backend for dc=example,dc=org..."
    dsconf localhost backend create --suffix "dc=example,dc=org" --be-name userroot
fi

# Check if base DN exists
if ldapsearch -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w admin -b "dc=example,dc=org" -s base &>/dev/null; then
    echo "Base DN already exists, skipping LDIF import"
else
    echo "Importing LDIF from /data/ldif/base.ldif..."
    ldapadd -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w admin -f /data/ldif/base.ldif
    echo "LDIF imported successfully!"

    # Run memberOf fixup to populate memberOf attributes for imported entries
    echo "Running memberOf fixup task..."
    dsconf localhost plugin memberof fixup "dc=example,dc=org"
    sleep 2
    echo "memberOf attributes populated!"
fi

echo "389 DS initialization complete!"
