#! /bin/bash
set -xe
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}
QUAYCONFIG=${QUAYCONFIG:-"$QUAYCONF/stack"}
CERTDIR=${CERTDIR:-"$QUAYCONFIG/extra_ca_certs"}
SYSTEM_CERTDIR=${SYSTEM_CERTDIR:-"/etc/pki/ca-trust/source/anchors"}
# PYTHONUSERBASE_SITE_PACKAGE=${PYTHONUSERBASE_SITE_PACKAGE:-"$(python -m site --user-site)"}
PYTHONUSERBASE_SITE_PACKAGE=/opt/app-root/lib/python3.12/site-packages

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
# to /etc/pki after because of permission issues

mkdir -p /tmp/extracted
rm -rf /etc/pki/ca-trust/extracted
update-ca-trust extract -o /tmp/extracted
chmod ug+w -R /tmp/extracted
mv /tmp/extracted /etc/pki/ca-trust
