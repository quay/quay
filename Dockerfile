FROM registry.access.redhat.com/ubi8/ubi-minimal:latest AS base
# Only set variables or install packages that need to end up in the
# final container here.
ENV PATH=/app/bin/:$PATH \
	PYTHONUNBUFFERED=1 \
	PYTHONIOENCODING=UTF-8 \
	LC_ALL=C.UTF-8 \
	LANG=C.UTF-8
ENV PYTHONUSERBASE /app
ENV TZ UTC
RUN set -ex\
	; microdnf -y module enable nginx:1.20 \
	; microdnf -y module enable python39:3.9 \
	; microdnf update -y \
	; microdnf -y --setopt=tsflags=nodocs install \
		dnsmasq \
		memcached \
		nginx \
		libpq-devel \
		openldap \
		openssl \
		python39 \
		python3-gpg \
		skopeo \
        findutils \
    ; microdnf remove platform-python-pip python39-pip \
	; microdnf -y clean all && rm -rf /var/cache/yum

# Config-editor builds the javascript for the configtool.
FROM registry.access.redhat.com/ubi8/nodejs-10 AS config-editor
WORKDIR /opt/app-root/src
# This argument must be repeated, and should have the same default as
# the other CONFIGTOOL_VERSION argument.
ARG CONFIGTOOL_VERSION=v0.1.15
RUN curl -fsSL "https://github.com/quay/config-tool/archive/${CONFIGTOOL_VERSION}.tar.gz"\
	| tar xz --strip-components=4 --exclude='*.go'
RUN set -ex\
	; npm install --quiet --no-progress --ignore-engines \
	; npm run --quiet build\
	; rm -Rf node_modules\
	;

# Build-python installs the requirements for the python code.
FROM base AS build-python
ENV PYTHONDONTWRITEBYTECODE 1
RUN set -ex\
	; microdnf -y --setopt=tsflags=nodocs install \
		gcc-c++ \
		git \
		openldap-devel \
		python39-devel \
		libffi-devel \
        openssl-devel \
        diffutils \
        file \
        make \
        libjpeg-turbo \
        libjpeg-turbo-devel \
		wget \
		rust-toolset \
	; microdnf -y clean all
WORKDIR /build
RUN python3 -m ensurepip --upgrade
COPY requirements.txt .
# Note that it installs into PYTHONUSERBASE because of the '--user'
# flag.

# When cross-compiling the container, cargo uncontrollably consumes memory and
# gets killed by the OOM Killer when it fetches dependencies. The workaround is
# to use the git executable.
# See https://github.com/rust-lang/cargo/issues/10583 for details.
ENV CARGO_NET_GIT_FETCH_WITH_CLI=true

# Added GRPC & Gevent support for IBMZ
# wget has been added to reduce the build time
# In Future if wget is to be removed , then uncomment below line for grpc installation on IBMZ i.e. s390x
# ENV GRPC_PYTHON_BUILD_SYSTEM_OPENSSL 1

RUN ARCH=$(uname -m) ; echo $ARCH; \
    if [ "$ARCH" == "ppc64le" ] ; then \
    GE_LATEST=$(grep "gevent" requirements.txt |cut -d "=" -f 3); \
	wget https://github.com/IBM/oss-ecosystem-gevent/releases/download/${GE_LATEST}/manylinux_ppc64le_wheels_${GE_LATEST}.tar.gz; \
	tar xvf manylinux_ppc64le_wheels_${GE_LATEST}.tar.gz; \
	python3 -m pip install --no-cache-dir --user wheelhouse/gevent-${GE_LATEST}-cp39-cp39-manylinux_2_17_ppc64le.manylinux2014_ppc64le.whl; \
    GRPC_LATEST=$(grep "grpcio" requirements.txt |cut -d "=" -f 3); \
	wget https://github.com/IBM/oss-ecosystem-grpc/releases/download/${GRPC_LATEST}/grpcio-${GRPC_LATEST}-cp39-cp39-linux_ppc64le.whl; \
	python3 -m pip install --no-cache-dir --user grpcio-${GRPC_LATEST}-cp39-cp39-linux_ppc64le.whl; \
	fi;\
    if [ "$ARCH" == "s390x" ] ; then \
    GRPC_LATEST=$(grep "grpcio" requirements.txt |cut -d "=" -f 3); \
        wget https://github.com/IBM/grpc-for-Z/releases/download/${GRPC_LATEST}/grpcio-${GRPC_LATEST}-cp39-cp39-linux_s390x.whl; \
	python3 -m pip install --no-cache-dir --user grpcio-${GRPC_LATEST}-cp39-cp39-linux_s390x.whl; \
    GEVENT_LATEST=$(grep "gevent" requirements.txt |cut -d "=" -f 3); \
        wget https://github.com/IBM/gevent-for-z/releases/download/${GEVENT_LATEST}/gevent-${GEVENT_LATEST}-cp39-cp39-linux_s390x.whl; \
	python3 -m pip install --no-cache-dir --user gevent-${GEVENT_LATEST}-cp39-cp39-linux_s390x.whl; \
    fi
RUN set -ex\
    ; python3 -m pip install --no-cache-dir --progress-bar off --user $(grep -e '^pip=' -e '^wheel=' -e '^setuptools=' ./requirements.txt) \
	; python3 -m pip install --no-cache-dir --progress-bar off --user --requirement requirements.txt \
	;
RUN set -ex\
# Doing this is explicitly against the purpose and use of certifi.
	; for dir in\
		$(find "$(python3 -m site --user-base)" -type d -name certifi)\
	; do chgrp -R 0 "$dir" && chmod -R g=u "$dir" ; done\
	;

# Build-static downloads the static javascript.
FROM registry.access.redhat.com/ubi8/nodejs-10 AS build-static
WORKDIR /opt/app-root/src
COPY --chown=1001:0 package.json package-lock.json  ./
RUN npm clean-install
COPY --chown=1001:0 static/  ./static/
COPY --chown=1001:0 *.json *.js  ./
RUN npm run --quiet build

# Build React UI
FROM registry.access.redhat.com/ubi8/nodejs-16:latest as build-ui
WORKDIR /opt/app-root
COPY --chown=1001:0 web/package.json web/package-lock.json  ./
RUN npm clean-install
COPY --chown=1001:0 web .
RUN npm run --quiet build

# Pushgateway grabs pushgateway.
FROM registry.access.redhat.com/ubi8/ubi:latest AS pushgateway
ENV OS=linux
ARG PUSHGATEWAY_VERSION=1.0.0
RUN set -ex\
	; ARCH=$(uname -m) ; echo $ARCH \
	; if [ "$ARCH" == "x86_64" ] ; then ARCH="amd64" ; elif [ "$ARCH" == "aarch64" ] ; then ARCH="arm64" ; fi \
	; curl -fsSL "https://github.com/prometheus/pushgateway/releases/download/v${PUSHGATEWAY_VERSION}/pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}.tar.gz"\
	| tar xz "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway"\
	; install "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" /usr/local/bin/pushgateway\
	;

# Config-tool builds the go binary in the configtool.
FROM registry.access.redhat.com/ubi8/go-toolset:1.17.12 as config-tool
WORKDIR /opt/app-root/src
ARG CONFIGTOOL_VERSION=v0.1.15
RUN curl -fsSL "https://github.com/quay/config-tool/archive/${CONFIGTOOL_VERSION}.tar.gz"\
	| tar xz --strip-components=1 --exclude '*/pkg/lib/editor/static/build'
COPY --from=config-editor /opt/app-root/src/static/build  /opt/app-root/src/pkg/lib/editor/static/build
RUN go install -tags=fips ./cmd/config-tool

FROM registry.access.redhat.com/ubi8/ubi-minimal AS build-quaydir
WORKDIR /quaydir
COPY --from=config-editor /opt/app-root/src /quaydir/config_app
COPY --from=build-static /opt/app-root/src/static /quaydir/static
COPY --from=build-ui /opt/app-root/dist /quaydir/static/patternfly

# Copy in source and update local copy of AWS IP Ranges.
# This is a bad place to do the curl, but there's no good place to do
# it except to have it checked in.
COPY --chown=0:0 . .
RUN set -ex\
	; chmod -R g=u .\
	; curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o util/ipresolver/aws-ip-ranges.json\
	;

# Final is the end container, where all the work from the other
# containers are copied in.
FROM base AS final
LABEL maintainer "quay-devel@redhat.com"

ENV QUAYDIR /quay-registry
ENV QUAYCONF /quay-registry/conf
ENV QUAYRUN /quay-registry/conf
ENV QUAYPATH $QUAYDIR
ENV PYTHONPATH $QUAYPATH

# All of these chgrp+chmod commands are an Openshift-ism.
#
# Openshift runs a container as a random UID and GID 0, so anything
# that's in the base image and needs to be modified at runtime needs
# to make sure it's group-writable.
RUN alternatives --set python /usr/bin/python3
RUN set -ex\
	; setperms() { for d in "$@"; do chgrp -R 0 "$d" && chmod -R g=u "$d" && ls -ld "$d"; done; }\
	; newdir() { for d in "$@"; do mkdir -m 775 "$d" && ls -ld "$d"; done; }\
# Allow TLS certs to be created and installed as non-root user.
# See also update-ca-trust(8).
	; setperms /etc/pki/ca-trust/extracted /etc/pki/ca-trust/source/anchors\
# Allow for nginx to run unprivledged.
	; setperms /etc/nginx\
	; ln -sf /dev/stdout /var/log/nginx/access.log\
	; ln -sf /dev/stdout /var/log/nginx/error.log\
# The code doesn't agree on where the configuration lives, so create a
# symlink.
	; ln -s $QUAYCONF /conf\
# Make a grip of runtime directories.
	; newdir /certificates "$QUAYDIR" "$QUAYDIR/conf" "$QUAYDIR/conf/stack" /datastorage\
# Another Openshift-ism: it doesn't bother picking a uid that means
# anything to the OS inside the container, so the process needs
# permissions to modify the user database.
	; setperms /etc/passwd\
	;

WORKDIR $QUAYDIR
# Ordered from least changing to most changing.
COPY --from=pushgateway /usr/local/bin/pushgateway /usr/local/bin/pushgateway
COPY --from=build-python /app /app
COPY --from=config-tool /opt/app-root/src/go/bin/config-tool /bin
COPY --from=build-quaydir /quaydir $QUAYDIR

EXPOSE 8080 8443 7443 9091 55443
# Don't expose /var/log as a volume, because we just configured it
# correctly above.
# It's probably unwise to mount /tmp as a volume but if someone must,
# make sure it's mode 1777 like /tmp should be.
VOLUME ["/datastorage", "/tmp", "/conf/stack"]
# In non-Openshift environments, drop privilege.
USER 1001
ENTRYPOINT ["dumb-init", "--", "/quay-registry/quay-entrypoint.sh"]
CMD ["registry"]
