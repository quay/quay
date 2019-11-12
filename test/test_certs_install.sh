#!/usr/bin/env bash

set -e

echo "> Starting certs install test"

# Set up all locations needed for the test
QUAYPATH=${QUAYPATH:-"."}
SCRIPT_LOCATION=${SCRIPT_LOCATION:-"/quay-registry/conf/init"}

# Parameters: (quay config dir, certifcate dir, number of certs expected).
function call_script_and_check_num_certs {
    QUAYCONFIG=$1 CERTDIR=$2 ${SCRIPT_LOCATION}/certs_install.sh
    if [ $? -ne 0 ]; then
        echo "Failed to install $3 certs"
        exit 1;
    fi

    certs_found=$(ls /etc/pki/ca-trust/source/anchors | wc -l)
    if [ ${certs_found} -ne "$3" ]; then
        echo "Expected there to be $3 in ca-certificates, found $certs_found"
        exit 1
    fi
}

# Create a dummy cert we can test to install
# echo '{"CN":"CA","key":{"algo":"rsa","size":2048}}' | cfssl gencert -initca - | cfssljson -bare test
openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 \
    -subj "/C=US/ST=NY/L=NYC/O=Dis/CN=self-signed" \
    -keyout test-key.pem  -out test.pem

# Create temp dirs we can test with
WORK_DIR=`mktemp -d`
CERTS_WORKDIR=`mktemp -d`

# deletes the temp directory
function cleanup {
  rm -rf "$WORK_DIR"
  rm -rf "$CERTS_WORKDIR"
  rm test.pem
  rm test-key.pem
}

# register the cleanup function to be called on the EXIT signal
trap cleanup EXIT

# Test calling with empty directory to not fail
call_script_and_check_num_certs ${WORK_DIR} ${CERTS_WORKDIR} 0
if [ "$?" -ne 0 ]; then
    echo "Failed to install certs with no files in the directory"
    exit 1
fi

# Move an ldap cert into the temp directory and test that installation
cp test.pem ${WORK_DIR}/ldap.crt
call_script_and_check_num_certs ${WORK_DIR} ${CERTS_WORKDIR} 1

# Move 1 cert to extra cert dir and test
cp test.pem ${CERTS_WORKDIR}/cert1.crt
call_script_and_check_num_certs ${WORK_DIR} ${CERTS_WORKDIR} 2


# Move another cert to extra cer dir and test all three exist
cp test.pem ${CERTS_WORKDIR}/cert2.crt
call_script_and_check_num_certs ${WORK_DIR} ${CERTS_WORKDIR} 3


echo "> Certs install script test succeeded"
exit 0
