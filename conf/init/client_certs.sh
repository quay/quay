#!/bin/bash

CERTDIR=${CERTDIR:-"/.postgresql"}

# only execute if we have the secrets for client certificates
if [ -d /run/secrets/postgresql ]; then
	if [ -d ${CERTDIR} ]; then
		[ -e /run/secrets/postgresql/tls.crt ] && \
			cp /run/secrets/postgresql/tls.crt ${CERTDIR}/postgresql.crt
		[ -e /run/secrets/postgresql/tls.key ] && \
			cp /run/secrets/postgresql/tls.key ${CERTDIR}/postgresql.key
		# SSL key needs to be restricted mode 0600
		[ -e ${CERTDIR}/postgresql.key ] && \
			chmod 0600 ${CERTDIR}/postgresql.key
		[ -e /run/secrets/postgresql/ca.crt ] && \
			cp /run/secrets/postgresql/ca.crt ${CERTDIR}/root.crt
		[ -e /run/secrets/postgresql/ca.crl ] && \
			cp /run/secrets/postgresql/ca.crl ${CERTDIR}/root.crl
	else
		# inidicate that we didn't succeed with creating the expected SSL store
		echo "cannot create ${CERTDIR}"
		exit 1
	fi
fi
exit 0
