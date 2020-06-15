#!/usr/bin/env bash

QUAYENTRY=${QUAYENTRY:=$1}
QUAYENTRY=${QUAYENTRY:=registry}

if ! whoami &> /dev/null; then
  if [ -w /etc/passwd ]; then
    echo "${USER_NAME:-default}:x:$(id -u):0:${USER_NAME:-default} user:${HOME}:/sbin/nologin" >> /etc/passwd
  fi
fi

display_usage() {
    echo "Usage: ${0} <registry|config|migrate|repomirror|shell|help>"
    echo
    echo "If the first argument isn't one of the above modes,"
    echo "the arguments will be exec'd directly, i.e.:"
    echo
    echo "  ${0} uptime"
}

if [[ "${QUAYENTRY}" = "help" ]]
then
    display_usage
    exit 0
fi


cat << "EOF"
   __   __
  /  \ /  \     ______   _    _     __   __   __
 / /\ / /\ \   /  __  \ | |  | |   /  \  \ \ / /
/ /  / /  \ \  | |  | | | |  | |  / /\ \  \   /
\ \  \ \  / /  | |__| | | |__| | / ____ \  | |
 \ \/ \ \/ /   \_  ___/  \____/ /_/    \_\ |_|
  \__/ \__/      \ \__
                  \___\ by Red Hat

 Build, Store, and Distribute your Containers


EOF

# Custom environment variables for use in conf/supervisord.conf
# The gunicorn-registry process DB_CONNECTION_POOLING must default to true
export DB_CONNECTION_POOLING_REGISTRY=${DB_CONNECTION_POOLING:-"true"}

case "$QUAYENTRY" in
    "shell")
        echo "Entering shell mode"
        exec /bin/bash
        ;;
    "config")
        echo "Entering config mode, only copying config-app entrypoints"
        : "${CONFIG_APP_PASSWORD:=$2}"
        : "${CONFIG_APP_PASSWORD:?Missing password argument for configuration tool}"
        printf '%s' "${CONFIG_APP_PASSWORD}" | openssl passwd -apr1 -stdin >> "$QUAYDIR/config_app/conf/htpasswd"

        "${QUAYPATH}/config_app/init/certs_create.sh" || exit
        "${QUAYPATH}/conf/init/certs_install.sh" || exit
        exec supervisord -c "${QUAYPATH}/config_app/conf/supervisord.conf" 2>&1
        ;;
    "migrate")
        : "${MIGRATION_VERSION:=$2}"
        : "${MIGRATION_VERSION:?Missing version argument}"
        echo "Entering migration mode to version: ${MIGRATION_VERSION}"
        PYTHONPATH="${QUAYPATH}" alembic upgrade "${MIGRATION_VERSION}"
        ;;
    "repomirror")
        echo "Entering repository mirroring mode"
        export QUAY_SERVICES="${QUAY_SERVICES}${QUAY_SERVICES:+,}repomirrorworker,pushgateway"
        ;&
    "registry-nomigrate")
        echo "Running all default registry services without migration"
        for f in "${QUAYCONF}"/init/*.sh; do
            if [ "$f" != "/quay-registry/conf/init/runmigration.sh" ]; then
                echo "Running init script '$f'"
                ENSURE_NO_MIGRATION=true "$f" || exit
            fi
        done
        exec supervisord -c "${QUAYCONF}/supervisord.conf" 2>&1
        ;;
    "registry")
        if [ -z "${QUAY_SERVICES}" ]; then
            echo "Running all default registry services"
        else
            echo "Running services ${QUAY_SERVICES}"
        fi
        for f in "${QUAYCONF}"/init/*.sh; do
            echo "Running init script '$f'"
            "$f" || exit
        done
        exec supervisord -c "${QUAYCONF}/supervisord.conf" 2>&1
        ;;
    *)
        echo "Running '$QUAYENTRY'"
        eval exec "$@"
        ;;
esac
