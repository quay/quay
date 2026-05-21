#! /bin/bash
set -e
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}
QUAYCONFIG=${QUAYCONFIG:-"$QUAYCONF/stack"}
CERTDIR=${CERTDIR:-"$QUAYCONFIG/extra_ca_certs"}
FALLBACK_QUAYCONFIG=${FALLBACK_QUAYCONFIG:-"/conf/stack"}
SYSTEM_CERTDIR=${SYSTEM_CERTDIR:-"/etc/pki/ca-trust/source/anchors"}
SYSTEM_TRUSTSTORE_BUNDLE=${SYSTEM_TRUSTSTORE_BUNDLE:-"/etc/pki/tls/certs/ca-bundle.crt"}
TRUSTSTORE_WAIT_TIMEOUT_SECONDS=${TRUSTSTORE_WAIT_TIMEOUT_SECONDS:-10}
if [ -f /etc/os-release ] && grep -q 'VERSION_ID="8' /etc/os-release; then
    PYTHONUSERBASE_SITE_PACKAGE=${PYTHONUSERBASE_SITE_PACKAGE:-"$(python -m site --user-site)"}
else
    PYTHONUSERBASE_SITE_PACKAGE=/opt/app-root/lib/python3.12/site-packages
fi
CERTIFI_BUNDLE=${CERTIFI_BUNDLE:-"$PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem"}

PREVIOUS_QUAYCONFIG=$QUAYCONFIG
if [ "$QUAYCONFIG" != "$FALLBACK_QUAYCONFIG" ] \
    && [ -f "$FALLBACK_QUAYCONFIG/config.yaml" ] \
    && [ ! -f "$QUAYCONFIG/config.yaml" ]; then
    QUAYCONFIG=$FALLBACK_QUAYCONFIG
    if [ "$CERTDIR" = "$PREVIOUS_QUAYCONFIG/extra_ca_certs" ]; then
        CERTDIR="$QUAYCONFIG/extra_ca_certs"
    fi
fi

cd ${QUAYDIR:-"/quay-registry"}

# Add the custom LDAP certificate
if [ -e $QUAYCONFIG/ldap.crt ]; then
    cp $QUAYCONFIG/ldap.crt ${SYSTEM_CERTDIR}/ldap.crt
fi

# Add extra trusted certificates (as a directory)
if [ -d $CERTDIR ]; then
    if test "$(ls -A "$CERTDIR")"; then
	echo "Installing extra certificates found in $CERTDIR directory"
	cp $CERTDIR/* ${SYSTEM_CERTDIR}

	CERT_FILES="$CERTDIR/*"

	for f in $CERT_FILES
	do
	    lastline=$(tail -c 1 $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem)

	    if [ "$lastline" != "" ]; then
		echo >> $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem
	    fi

	    cat $f >> $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem
	done
    fi
fi

# Add extra trusted certificates (as a file)
if [ -f $CERTDIR ]; then
    echo "Installing extra certificates found in $CERTDIR file"
    csplit -z -f ${SYSTEM_CERTDIR}/extra-ca- $CERTDIR  '/-----BEGIN CERTIFICATE-----/' '{*}'

    lastline=$(tail -c 1 $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem)

    if [ "$lastline" != "" ]; then
	echo >> $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem
    fi

    cat $CERTDIR >> $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem
fi

# Add extra trusted certificates (prefixed)
for f in $(find -L $QUAYCONFIG/ -maxdepth 1 -type f -name "extra_ca*")
do
    echo "Installing extra cert $f"
    cp "$f" ${SYSTEM_CERTDIR}

    lastline=$(tail -c 1 $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem)
    if [ "$lastline" != "" ]; then
	echo >> $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem
    fi

    cat "$f" >> $PYTHONUSERBASE_SITE_PACKAGE/certifi/cacert.pem
done

# Update all CA certificates.
# hack for UBI9, extract it a temp location and move
# to /etc/pki after because of permission issues.
# All ubi8 specific code should be removed after UBI9 is fully supported, see PROJQUAY-9013
if [ -f /etc/os-release ] && grep -q 'VERSION_ID="8' /etc/os-release; then
    update-ca-trust extract
else
    mkdir -p /tmp/extracted
    rm -rf /etc/pki/ca-trust/extracted
    update-ca-trust extract -o /tmp/extracted
    chmod ug+w -R /tmp/extracted
    mv /tmp/extracted /etc/pki/ca-trust
fi

for ((i=0; i<TRUSTSTORE_WAIT_TIMEOUT_SECONDS; i++)); do
    if [ -s "$SYSTEM_TRUSTSTORE_BUNDLE" ] \
        && [ -s "$CERTIFI_BUNDLE" ] \
        && grep -q "BEGIN CERTIFICATE" "$SYSTEM_TRUSTSTORE_BUNDLE" \
        && grep -q "BEGIN CERTIFICATE" "$CERTIFI_BUNDLE"; then
        exit 0
    fi
    sleep 1
done

echo "Timed out waiting for trust store readiness: $SYSTEM_TRUSTSTORE_BUNDLE / $CERTIFI_BUNDLE"
exit 1
