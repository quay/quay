# LDAP Setup for Quay Local Development

This directory contains LDAP configuration files for testing Quay with LDAP authentication using **389 Directory Server**.

## Files

- `base.ldif`: Base LDAP structure with sample users
- `ldap-config.yaml`: LDAP-specific configuration to merge into config.yaml
- `init-389ds.sh`: Initialization script that creates the backend and imports LDIF

## Quick Start

### 1. Start 389 DS LDAP Container

```bash
# Start LDAP service (389 Directory Server)
docker-compose up -d ldap

# Or with podman
podman-compose up -d ldap

# Check container logs (389 DS takes ~40 seconds to initialize and import LDIF)
docker-compose logs -f ldap

# Wait for "389 DS initialization complete!" message

# Verify users were loaded
podman exec quay-ldap ldapsearch -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w admin \
  -b "ou=users,dc=example,dc=org" "(objectClass=inetOrgPerson)" dn
```

The LDIF file is automatically imported on first startup by the `init-389ds.sh` script. **No manual steps needed!**

### 2. Enable LDAP in Quay Config

```bash
# Merge LDAP config into your existing config.yaml
make enable-ldap

# Restart Quay to apply changes
docker-compose restart quay
```

**What this does:**
- Backs up your current config to `config.yaml.backup`
- Merges LDAP settings from `ldap-config.yaml` using `yq`
- Sets `AUTHENTICATION_TYPE: LDAP` and adds all LDAP connection details
- Uses `cn=Directory Manager` as admin DN (389 DS default)

**Requirements:**
- `yq` v4+ must be installed (https://github.com/mikefarah/yq/)
  - Linux: `wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq && chmod +x /usr/local/bin/yq`
  - macOS: `brew install yq`
  - Or see: https://github.com/mikefarah/yq/#install

## LDAP Structure

```
dc=example,dc=org
├── cn=Directory Manager (389 DS admin - auto-created)
└── ou=users,dc=example,dc=org
    ├── uid=admin,ou=users,dc=example,dc=org
    ├── uid=user1,ou=users,dc=example,dc=org
    ├── uid=quayadmin,ou=users,dc=example,dc=org
    ├── uid=readonly,ou=users,dc=example,dc=org
    └── uid=testuser,ou=users,dc=example,dc=org
```

## Sample Users

All users have the password: `password`

| Username   | Email                 | Quay Role              |
|------------|-----------------------|------------------------|
| admin      | admin@example.com     | Superuser              |
| user1      | user1@example.com     | Superuser              |
| quayadmin  | quayadmin@example.com | Superuser + Read-only  |
| readonly   | readonly@example.com  | Read-only Superuser    |
| testuser   | testuser@example.com  | Regular user           |

## Quay Configuration

The LDAP config (`ldap-config.yaml`) sets up Quay to connect to 389 DS:

- **LDAP URI**: `ldap://quay-ldap:3389`
- **Admin DN**: `cn=Directory Manager`
- **Admin Password**: `admin`
- **Base DN**: `dc=example,dc=org`
- **User RDN**: `ou=users`

## Testing LDAP Connection

You can test the LDAP connection using `ldapsearch` or 389 DS tools:

```bash
# Using ldapsearch (search for all users)
ldapsearch -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w admin -b "ou=users,dc=example,dc=org"

# Using 389 DS native tools (list all users)
podman exec quay-ldap dsidm localhost user list

# Get specific user details
podman exec quay-ldap dsidm localhost user get admin

# Search for specific user with ldapsearch
ldapsearch -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w admin -b "ou=users,dc=example,dc=org" "(uid=admin)"
```

## Troubleshooting

### Container Takes Long to Start
- 389 DS initialization takes ~30 seconds on first startup
- Watch logs: `docker-compose logs -f ldap`
- Wait for "INFO: 389-ds-container started" message

### Connection Refused
- Ensure LDAP container is running on port 3389
- Verify 389 DS is fully initialized (check logs)

### Authentication Failed
- Admin DN is `cn=Directory Manager` (not `cn=admin`)
- Verify admin password is `admin`
- Check that base.ldif was loaded successfully

### Users Not Found
- Verify the LDIF was loaded: `podman exec quay-ldap dsidm localhost user list`
- Or use ldapsearch: `ldapsearch -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w admin -b "dc=example,dc=org"`
- Check Quay logs for LDAP query details
- Check 389 DS logs: `docker-compose logs ldap`

## Adding More Users

To add more users, create a new LDIF file following this template:

```ldif
dn: uid=newuser,ou=users,dc=example,dc=org
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
uid: newuser
sn: User
givenName: New
cn: New User
displayName: New User
uidNumber: 10005
gidNumber: 10005
userPassword: password
gecos: New User
loginShell: /bin/bash
homeDirectory: /home/newuser
mail: newuser@example.com
```

Then load it:

```bash
# Copy LDIF into container
docker cp newuser.ldif quay-ldap:/tmp/newuser.ldif

# Import using ldapadd
docker exec quay-ldap ldapadd -x -D "cn=Directory Manager" -w admin -f /tmp/newuser.ldif

# Or use 389 DS native tools
docker exec quay-ldap dsidm localhost user create --uid newuser --cn "New User" --displayName "New User" --uidNumber 10005 --gidNumber 10005 --homeDirectory /home/newuser
```
