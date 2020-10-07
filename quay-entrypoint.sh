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
export CONFIG_APP_PASSWORD=${CONFIG_APP_PASSWORD:-"\"\""}
export OPERATOR_ENDPOINT=${OPERATOR_ENDPOINT:-"\"\""}

case "$QUAYENTRY" in
    "shell")
        echo "Entering shell mode"
        exec /bin/bash
        ;;
    "config")
        if [ -z "${QUAY_SERVICES}" ]; then
            echo "Running all default config services"
        else
            echo "Running services ${QUAY_SERVICES}"
        fi
        if [ $CONFIG_APP_PASSWORD = "\"\"" ]; then    
            CONFIG_APP_PASSWORD=$2
        fi
        : "${CONFIG_APP_PASSWORD:?Missing password argument for configuration tool}"
        export CONFIG_APP_PASSWORD="${CONFIG_APP_PASSWORD}"
        printf '%s' "${CONFIG_APP_PASSWORD}" | openssl passwd -apr1 -stdin >> "$QUAYDIR/config_app/conf/htpasswd"

        if [ $OPERATOR_ENDPOINT = "\"\"" ]; then
            if [ -n "$3" ]; then
                OPERATOR_ENDPOINT=$3
            fi
        fi
        export OPERATOR_ENDPOINT="${OPERATOR_ENDPOINT}"

        "${QUAYPATH}/conf/init/certs_create.sh" || exit
        "${QUAYPATH}/conf/init/certs_install.sh" || exit
        "${QUAYPATH}/conf/init/supervisord_conf_create.sh" config || exit
        exec supervisord -c "${QUAYCONF}/supervisord.conf" 2>&1
        ;;
    "migrate")
        : "${MIGRATION_VERSION:=$2}"
        : "${MIGRATION_VERSION:?Missing version argument}"
        echo "Entering migration mode to version: ${MIGRATION_VERSION}"
        PYTHONPATH="${QUAYPATH}" alembic upgrade "${MIGRATION_VERSION}"
        ;;
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
    "repomirror")
        echo "Entering repository mirroring mode"
        export QUAY_SERVICES="${QUAY_SERVICES}${QUAY_SERVICES:+,}repomirrorworker,pushgateway"
        ;&
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