#! /bin/bash
set -e
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}
cd ${QUAYDIR:-"/"}
SYSTEM_CERTDIR=${SYSTEM_CERTDIR:-"/etc/pki/ca-trust/source/anchors"}
# Create certs for jwtproxy to mitm outgoing TLS connections
# echo '{"CN":"CA","key":{"algo":"rsa","size":2048}}' | cfssl gencert -initca - | cfssljson -bare mitm
mkdir -p /certificates; cd /certificates
openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 \
    -subj "/C=US/ST=NY/L=NYC/O=Dis/CN=self-signed" \
    -keyout mitm-key.pem  -out mitm.pem
cp /certificates/mitm-key.pem $QUAYCONF/mitm.key
cp /certificates/mitm.pem $QUAYCONF/mitm.cert
cp /certificates/mitm.pem $SYSTEM_CERTDIR/mitm.crt
