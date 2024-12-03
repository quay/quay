
/^RUN ARCH=$(uname -m) ; echo $ARCH; .*/,/^RUN /{
	/^RUN set/!d
}

/^FROM .* [Aa][Ss] config-tool/,/^FROM /{
	s|go install -tags=|GOEXPERIMENT=strictfipsruntime go install -tags strictfipsruntime,|
}

/^FROM .* [Aa][Ss] build-quaydir$/,/^FROM /{
	\|	; curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o util/ipresolver/aws-ip-ranges.json\\|d
}

/^FROM .* [Aa][Ss] final$/,/^FROM /{
	/^LABEL maintainer "quay-devel@redhat.com"/{
		i\
LABEL com.redhat.component="quay-registry-container"\
LABEL name="quay/quay-rhel8"\
LABEL io.k8s.display-name="Red Hat Quay"\
LABEL io.k8s.description="Red Hat Quay"\
LABEL summary="Red Hat Quay"\
LABEL maintainer="support@redhat.com"\
LABEL io.openshift.tags="quay"\
LABEL description="Red Hat Quay"\
LABEL vendor="Red Hat, Inc."
ENV RED_HAT_QUAY=true
		d
	}
}
