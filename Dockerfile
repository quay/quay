FROM registry.access.redhat.com/ubi8/ubi:latest AS base
# Only set variables or install packages that need to end up in the
# final container here.
ENV PATH=/app/bin/:$PATH \
	PYTHONUNBUFFERED=1 \
	PYTHONIOENCODING=UTF-8 \
	LC_ALL=C.UTF-8 \
	LANG=C.UTF-8
ENV QUAYDIR /quay-registry
ENV QUAYCONF /quay-registry/conf
ENV QUAYRUN /quay-registry/conf
ENV QUAYPATH $QUAYDIR
ENV PYTHONUSERBASE /app
ENV PYTHONPATH $QUAYPATH
RUN set -ex\
	; dnf -y module enable nginx:1.20 \
	; dnf -y module enable python39:3.9 \
	; dnf -y -q --setopt=tsflags=nodocs --setopt=skip_missing_names_on_install=False install\
		dnsmasq \
		memcached \
		nginx \
		libpq-devel \
		openldap \
		openssl \
		python39 \
		python3-gpg \
		skopeo \
	; dnf -y -q clean all

# Config-editor builds the javascript for the configtool.
FROM registry.access.redhat.com/ubi8/nodejs-10 AS config-editor
WORKDIR /opt/app-root/src
# This argument must be repeated, and should have the same default as
# the other CONFIGTOOL_VERSION argument.
ARG CONFIGTOOL_VERSION=v0.1.12
RUN curl -fsSL "https://github.com/quay/config-tool/archive/${CONFIGTOOL_VERSION}.tar.gz"\
	| tar xz --strip-components=4 --exclude='*.go'
RUN set -ex\
	; npm install --quiet --no-progress --ignore-engines\
	; npm run --quiet build\
	;

# Build-python installs the requirements for the python code.
FROM base AS build-python
ENV PYTHONDONTWRITEBYTECODE 1
RUN set -ex\
	; dnf -y -q --setopt=tsflags=nodocs --setopt=skip_missing_names_on_install=False install\
		gcc-c++\
		git\
		openldap-devel\
		python39-devel\
		libffi-devel\
        openssl-devel \
        diffutils \
        file \
        make \
        libjpeg-turbo \
        libjpeg-turbo-devel \
		wget\
	; dnf -y -q clean all
WORKDIR /build
COPY requirements.txt .
# Note that it installs into PYTHONUSERBASE because of the '--user'
# flag.
RUN ARCH=$(uname -m) ; echo $ARCH; \
    if [ "$ARCH" == "ppc64le" ] ; then \
    GE_LATEST=$(grep "gevent" requirements.txt |cut -d "=" -f 3); \
	wget https://github.com/IBM/oss-ecosystem-gevent/releases/download/${GE_LATEST}/manylinux_ppc64le_wheels_${GE_LATEST}.tar.gz; \
	tar xvf manylinux_ppc64le_wheels_${GE_LATEST}.tar.gz; \
	python3 -m pip install --no-cache-dir --user wheelhouse/gevent-${GE_LATEST}-cp39-cp39-manylinux_2_17_ppc64le.manylinux2014_ppc64le.whl; \
    GRPC_LATEST=$(grep "grpcio" requirements.txt |cut -d "=" -f 3); \
	wget https://github.com/IBM/oss-ecosystem-grpc/releases/download/${GRPC_LATEST}/grpcio-${GRPC_LATEST}-cp39-cp39-linux_ppc64le.whl; \
	python3 -m pip install --no-cache-dir --user grpcio-${GRPC_LATEST}-cp39-cp39-linux_ppc64le.whl; \
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
COPY --chown=1001:0 static/  ./static/
COPY --chown=1001:0 *.json *.js  ./
RUN set -ex\
	; npm install --quiet --no-progress --ignore-engines\
	; npm run --quiet build\
	;

FROM registry.access.redhat.com/ubi8/nodejs-16:latest as build-ui
WORKDIR /opt/app-root

# Invalidate quay-ui cache if quay-ui main has changed
ADD https://api.github.com/repos/quay/quay-ui/git/ref/heads/main version.json
RUN git clone https://github.com/quay/quay-ui.git

RUN cd quay-ui &&\
	set -ex &&\
	npm install --quiet --no-progress --ignore-engines

RUN	cd quay-ui &&\
	npm run --quiet build

RUN chown -R 1001:0 quay-ui/dist 

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
FROM registry.access.redhat.com/ubi8/go-toolset:1.16.12 as config-tool
WORKDIR /opt/app-root/src
ARG CONFIGTOOL_VERSION=v0.1.12
RUN curl -fsSL "https://github.com/quay/config-tool/archive/${CONFIGTOOL_VERSION}.tar.gz"\
	| tar xz --strip-components=1 --exclude '*/pkg/lib/editor/static/build'
COPY --from=config-editor /opt/app-root/src/static/build  /opt/app-root/src/pkg/lib/editor/static/build
RUN go install ./cmd/config-tool

# Final is the end container, where all the work from the other
# containers are copied in.
FROM base AS final
LABEL maintainer "quay-devel@redhat.com"

# All of these chgrp+chmod commands are an Openshift-ism.
#
# Openshift runs a container as a random UID and GID 0, so anything
# that's in the base image and needs to be modified at runtime needs
# to make sure it's group-writable.
RUN alternatives --set python /usr/bin/python3
RUN set -ex\
	; setperms() { for d in "$@"; do chgrp -R 0 "$d" && chmod -R g=u "$d" && ls -ld "$d"; done; }\
	; newdir() { for d in "$@"; do mkdir -m g+w "$d" || { mkdir -p "$d" && chgrp 0 "$d" && chmod g=u "$d"; }; ls -ld "$d"; done; }\
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
	; newdir /certificates /quay-registry/conf/stack /datastorage\
# Another Openshift-ism: it doesn't bother picking a uid that means
# anything to the OS inside the container, so the process needs
# permissions to modify the user database.
	; setperms /etc/passwd\
	;

WORKDIR $QUAYDIR
RUN mkdir ${QUAYDIR}/config_app
# Ordered from least changing to most changing.
COPY --from=pushgateway /usr/local/bin/pushgateway /usr/local/bin/pushgateway
COPY --from=build-python /app /app
COPY --from=config-tool /opt/app-root/src/go/bin/config-tool /bin
COPY --from=config-editor /opt/app-root/src ${QUAYDIR}/config_app
COPY --from=build-static /opt/app-root/src/static ${QUAYDIR}/static
COPY --from=build-ui /opt/app-root/quay-ui/dist ${QUAYDIR}/static/patternfly

# Copy in source and update local copy of AWS IP Ranges.
# This is a bad place to do the curl, but there's no good place to do
# it except to have it checked in.
COPY --chown=0:0 . ${QUAYDIR}
RUN set -ex\
	; chmod -R g=u "${QUAYDIR}"\
	; curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o util/ipresolver/aws-ip-ranges.json\
	;

RUN rm -Rf node_modules config_app/node_modules

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
