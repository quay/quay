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
        if [ -z "$2" ]
        then
            if [ -z "${CONFIG_APP_PASSWORD}" ]
            then
                echo "Missing password for configuration tool"
                exit
            else
                openssl passwd -apr1 "${CONFIG_APP_PASSWORD}" >> $QUAYDIR/config_app/conf/htpasswd
            fi
        else
            openssl passwd -apr1 "$2" >> $QUAYDIR/config_app/conf/htpasswd
        fi

        ${QUAYPATH}/config_app/init/certs_create.sh 2>&1
        supervisord -c ${QUAYPATH}/config_app/conf/supervisord.conf 2>&1
        ;;
    "migrate")
        echo "Entering migration mode to version: ${2}"
        exec /usr/bin/scl enable python27 rh-nginx112 "PYTHONPATH=${QUAYPATH} alembic upgrade ${2}"
        ;;
    "repomirror")
        echo "Entering repository mirroring mode"
        if [ -z "${QUAY_SERVICES}" ]
        then
            export QUAY_SERVICES=repomirrorworker,pushgateway
        else
            export QUAY_SERVICES=${QUAY_SERVICES},repomirrorworker,pushgateway
        fi
        ;&
    "registry")
        if [ -z "${QUAY_SERVICES}" ]
        then
            echo "Running all default registry services"
        else
            echo "Running services ${QUAY_SERVICES}"
        fi
        for f in $(ls ${QUAYCONF}/init/*.sh); do
            echo "Running init script '$f'"
            $f || exit -1;
        done
        exec supervisord -c ${QUAYCONF}/supervisord.conf 2>&1
        ;;
    *)
        echo "Running '$QUAYENTRY'"
        exec $QUAYENTRY || exit -1
        ;;
esac

