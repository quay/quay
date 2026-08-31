# Setting up Clair on standalone deployments

This guide describes how to configure Clair on a standalone Project Quay deployment without the configuration tool web UI. As of Quay 3.17, the configuration tool UI was removed from the Quay image ([quay/quay#4769](https://github.com/quay/quay/pull/4769)). Enable security scanning by editing `config.yaml` directly.

For local development, use `make local-dev-up-with-clair` instead of following this guide. See [Getting Started](./getting-started.md#running-quay-for-development).

> **Evaluation only:** The examples below use unencrypted HTTP between Quay and Clair and PostgreSQL with `sslmode=disable` on a single host. Do not use this transport configuration in production. For production deployments, terminate TLS at a load balancer or reverse proxy, use HTTPS for Quay–Clair traffic, and configure PostgreSQL with `sslmode=verify-full` (or `verify-ca`) plus the required CA certificates.

## Overview

To configure Clair on a standalone deployment:

1. Deploy a PostgreSQL database for Clair.
2. Create a Clair `config.yaml` and start the Clair container.
3. Update the Quay `config.yaml` with security scanner settings.
4. Restart Quay.

## Deploy a Clair PostgreSQL database

In your Quay installation directory, create a directory for Clair database data:

```shell
mkdir /home/<user-name>/quay-poc/postgres-clairv4
```

Set permissions for the database data directory:

```shell
setfacl -m u:26:-wx /home/<user-name>/quay-poc/postgres-clairv4
```

Deploy PostgreSQL 15 for Clair (replace the password placeholders with strong values):

```shell
sudo podman run -d --name postgresql-clairv4 \
  -e POSTGRESQL_USER=clairuser \
  -e POSTGRESQL_PASSWORD=<clair-db-password> \
  -e POSTGRESQL_DATABASE=clair \
  -e POSTGRESQL_ADMIN_PASSWORD=<postgres-admin-password> \
  -p 5433:5432 \
  -v /home/<user-name>/quay-poc/postgres-clairv4:/var/lib/pgsql/data:Z \
  registry.redhat.io/rhel8/postgresql-15
```

Install the `uuid-ossp` extension:

```shell
sudo podman exec -it postgresql-clairv4 /bin/bash -c \
  'echo "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"" | psql -d clair -U postgres'
```

Clair requires the `uuid-ossp` extension. If your database user lacks privileges to create extensions, add the extension before starting Clair. Without it, Clair fails with: `ERROR: Please load the "uuid-ossp" extension. (SQLSTATE 42501)`.

## Generate a pre-shared key (PSK)

Generate a base64-encoded PSK for Clair authentication:

```shell
openssl rand -base64 16
```

Use the same value in both Clair and Quay configuration.

## Configure and start Clair

Create a directory for Clair configuration (requires root for `/etc/opt`):

```shell
sudo mkdir -p /etc/opt/clairv4/config
cd /etc/opt/clairv4/config
```

Create `config.yaml` with a text editor or `sudo tee` (replace hostnames, credentials, and the PSK with your values):

```yaml
http_listen_addr: :8081
introspection_addr: :8088
log_level: debug
indexer:
  connstring: host=quay-server.example.com port=5433 dbname=clair user=clairuser password=<clair-db-password> sslmode=disable
  scanlock_retry: 10
  layer_scan_concurrency: 5
  migrations: true
matcher:
  connstring: host=quay-server.example.com port=5433 dbname=clair user=clairuser password=<clair-db-password> sslmode=disable
  max_conn_pool: 100
  migrations: true
  indexer_addr: clair-indexer
notifier:
  connstring: host=quay-server.example.com port=5433 dbname=clair user=clairuser password=<clair-db-password> sslmode=disable
  delivery_interval: 1m
  poll_interval: 5m
  migrations: true
  webhook:
    target: "http://quay-server.example.com:8080/secscan/notification"
    callback: "http://quay-server.example.com:8081/notifier/api/v1/notification"
auth:
  psk:
    key: "<base64-encoded-psk>"
    iss: ["quay"]
metrics:
  name: "prometheus"
```

Start Clair in combo mode:

```shell
sudo podman run -d --name clairv4 \
  -p 8081:8081 -p 8088:8088 \
  -e CLAIR_CONF=/clair/config.yaml \
  -e CLAIR_MODE=combo \
  -v /etc/opt/clairv4/config:/clair:Z \
  quay.io/projectquay/clair:4.7.2
```

Use a port that is not already in use on the Quay host for `http_listen_addr` (for example, `8081`). If you change `http_listen_addr`, also update the Podman `-p` port mapping, `SECURITY_SCANNER_V4_ENDPOINT` in Quay, and the notifier `webhook.callback` URL. Keep `webhook.target` on Quay's HTTP port, and change it only if Quay's HTTP listener changes.

## Configure Quay for security scanning

Edit your Quay `config.yaml` (for example, `$QUAY/config/config.yaml`) and add or update:

```yaml
FEATURE_SECURITY_SCANNER: true
SECURITY_SCANNER_V4_ENDPOINT: http://quay-server.example.com:8081
SECURITY_SCANNER_V4_PSK: "<base64-encoded-psk>"
SECURITY_SCANNER_ISSUER_NAME: quay
FEATURE_SECURITY_NOTIFICATIONS: true
```

- `SECURITY_SCANNER_V4_ENDPOINT` must reach Clair's HTTP listener from the Quay container.
- `SECURITY_SCANNER_V4_PSK` must match the `auth.psk.key` value in Clair's configuration.
- `SECURITY_SCANNER_ISSUER_NAME` must match an entry in Clair's `auth.psk.iss` list (both are `quay` in the examples above).
- Set `FEATURE_SECURITY_NOTIFICATIONS` to `true` when using Clair's notifier webhook.

Optionally validate `config.yaml` with the config-tool CLI (validation only; no web UI):

```shell
podman run --rm -v $QUAY/config:/conf/stack:Z \
  quay.io/projectquay/quay:latest \
  config-tool validate -c /conf/stack -m offline
```

Restart the Quay registry container to load the updated configuration.

## Verify

Push an image to Quay and confirm vulnerability data appears on the repository tag page after indexing completes.
