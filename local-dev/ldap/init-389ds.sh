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

# Check if base DN exists (anonymous search)
if ldapsearch -x -H ldap://localhost:3389 -b "dc=example,dc=org" -s base &>/dev/null; then
    echo "Base DN already exists, skipping LDIF import"
else
    echo "Importing LDIF from /data/ldif/base.ldif..."
    ldapadd -H "$LDAPI_URI" -Y EXTERNAL -f /data/ldif/base.ldif 2>&1 | grep -v "^SASL" || true
    echo "LDIF imported successfully!"
fi

# Enable MemberOf plugin so LDAP team sync can resolve group members via
# (memberOf=<group_dn>) filter. Requires a restart to take effect; dscontainer -r
# (the container entrypoint) restarts ns-slapd automatically when it exits.
# After restart, fixup populates memberOf back-links on existing group members.
echo "Enabling MemberOf plugin..."
dsconf localhost plugin memberof enable 2>&1 || true

echo "Restarting 389 DS to activate MemberOf plugin..."
kill -TERM "$(pgrep -f 'ns-slapd' | head -1)" 2>/dev/null || true
sleep 5

timeout=60
while [ $timeout -gt 0 ]; do
    if ldapsearch -x -H ldap://localhost:3389 -b "" -s base &>/dev/null; then
        echo "389 DS is ready after restart!"
        break
    fi
    sleep 1
    timeout=$((timeout - 1))
done

if [ $timeout -le 0 ]; then
    echo "WARNING: 389 DS did not restart within timeout, memberOf back-links unavailable"
else
    echo "Running MemberOf fixup to populate memberOf attributes for existing group members..."
    dsconf localhost plugin memberof fixup -b "dc=example,dc=org" 2>&1 || true
    sleep 10
    echo "MemberOf fixup complete"
fi

echo "389 DS initialization complete!"
