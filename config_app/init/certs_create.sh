#! /bin/bash
set -e
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}
cd ${QUAYDIR:-"/"}

if [ -f "$QUAYCONF/stack/ssl.key" ] && [ -f "$QUAYCONF/stack/ssl.cert" ]; then
    echo 'Using mounted ssl certs for quay-config app'
    cp $QUAYCONF/stack/ssl.key $QUAYDIR/config_app/quay-config.key
    cp $QUAYCONF/stack/ssl.cert $QUAYDIR/config_app/quay-config.cert
else
    echo 'Creating self-signed certs for quay-config app'

    # Create certs to secure connections while uploading config for secrets
    # echo '{"CN":"CA","key":{"algo":"rsa","size":2048}}' | cfssl gencert -initca - | cfssljson -bare quay-config
    mkdir -p /certificates; cd /certificates
    if [ -z "$QUAY_CONFIG_HOSTNAME" ];      then
        openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 \
            -subj "/C=US/ST=NY/L=NYC/O=Dis/CN=self-signed" \
            -keyout quay-config-key.pem  -out quay-config.pem
        else
        openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 \
            -subj "/C=US/ST=NY/L=NYC/O=Dis/CN=${QUAY_CONFIG_HOSTNAME}" \
            -keyout quay-config-key.pem  -out quay-config.pem
    fi
    cp /certificates/quay-config-key.pem $QUAYDIR/config_app/quay-config.key
    cp /certificates/quay-config.pem $QUAYDIR/config_app/quay-config.cert
fi
