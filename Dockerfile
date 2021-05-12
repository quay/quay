# syntax=docker/dockerfile:1.2
# Stream swaps to CentOS Stream once and is reused.
FROM docker.io/library/centos:8 AS stream
RUN set -ex\
	; dnf -y -q install centos-release-stream\
	; dnf -y -q swap centos-{linux,stream}-repos\
# This "|| true" is needed if building in podman, it seems.
# The filesystem package tries to modify permissions on /proc.
	; dnf -y -q distro-sync || true\
	; dnf -y -q clean all

# Base is set up with the runtime dependencies and environment.
FROM stream AS base
# Only set variables or install packages that need to end up in the
# final container here.
ENV PATH=/app/bin/:$PATH \
	PYTHONUNBUFFERED=1 \
	PYTHONIOENCODING=UTF-8 \
	LC_ALL=C.UTF-8 \
	LANG=C.UTF-8
ENV QUAYDIR /quay-registry
ENV QUAYCONF /quay-registry/conf
ENV QUAYPATH $QUAYDIR
ENV PYTHONUSERBASE /app
ENV PYTHONPATH $QUAYPATH
RUN set -ex\
	; dnf -y -q --setopt=tsflags=nodocs --setopt=skip_missing_names_on_install=False install\
		dnsmasq \
		memcached \
		nginx \
		openldap \
		openssl \
		python3 \
		python3-gpg \
		skopeo \
	; dnf -y -q clean all

# Build has all the build-only tools.
FROM base AS build
ENV PYTHONDONTWRITEBYTECODE 1
RUN set -ex\
	; dnf -y -q --setopt=tsflags=nodocs --setopt=skip_missing_names_on_install=False install\
		gcc-c++\
		git\
		nodejs\
		openldap-devel\
		python3-devel\
	; dnf -y -q clean all
WORKDIR /build

# Config-editor builds the javascript for the configtool.
FROM build AS config-editor
# This argument must be repeated, and should have the same default as
# the other CONFIGTOOL_VERSION argument.
ARG CONFIGTOOL_VERSION=master
RUN curl -fsSL "https://github.com/quay/config-tool/archive/${CONFIGTOOL_VERSION}.tar.gz"\
	| tar xz --strip-components=4 --exclude=static --exclude='*.go'\
		'*/pkg/lib/editor'
RUN set -ex\
	; npm install --quiet --no-progress --ignore-engines\
	; npm run --quiet build\
	;

# Build-python installs the requirements for the python code.
FROM build AS build-python
COPY requirements.txt .
# Note that it installs into PYTHONUSERBASE because of the '--user'
# flag.
RUN set -ex\
	; python3 -m pip install --no-cache-dir --quiet\
		--upgrade setuptools pip\
	; python3 -m pip install --no-cache-dir --progress-bar off\
		--user --requirement requirements.txt --no-cache\
	;
RUN set -ex\
# Doing this is explicitly against the purpose and use of certifi.
	; for dir in\
		$(find "$(python3 -m site --user-base)" -type d -name certifi)\
	; do chgrp -R 0 "$dir" && chmod -R g=u "$dir" ; done\
	;

# Build-static downloads the static javascript.
FROM build-python AS build-static
# The external library versions rarely change, do them first.
COPY external_libraries.py _init.py ./
RUN set -ex\
	; mkdir -p static/{webfonts,fonts,ldn}\
	; python3 -m external_libraries\
	;
# Now copy in the js and the control files.
# As far as I can tell, this needs to be done in two steps.
COPY --chown=0:0 static/  ./static/
COPY --chown=0:0 *.json *.js  ./
RUN set -ex\
	; npm install --quiet --no-progress --ignore-engines\
	; npm run --quiet build\
	;

# Jwtproxy grabs jwtproxy.
FROM stream as jwtproxy
ENV OS=linux ARCH=amd64 
ARG JWTPROXY_VERSION=0.0.3
RUN set -ex\
	; curl -fsSL -o /usr/local/bin/jwtproxy "https://github.com/coreos/jwtproxy/releases/download/v${JWTPROXY_VERSION}/jwtproxy-${OS}-${ARCH}"\
	; chmod +x /usr/local/bin/jwtproxy\
	;

# Pushgateway grabs pushgateway.
FROM stream AS pushgateway
ENV OS=linux ARCH=amd64 
ARG PUSHGATEWAY_VERSION=1.0.0
RUN set -ex\
	; curl -fsSL "https://github.com/prometheus/pushgateway/releases/download/v${PUSHGATEWAY_VERSION}/pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}.tar.gz"\
	| tar xz "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway"\
	; install "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" /usr/local/bin/pushgateway\
	;

# Config-tool builds the go binary in the configtool.
FROM docker.io/library/golang:1.15 as config-tool
WORKDIR /go/src/config-tool
ARG CONFIGTOOL_VERSION=master
RUN curl -fsSL "https://github.com/quay/config-tool/archive/${CONFIGTOOL_VERSION}.tar.gz"\
	| tar xz --strip-components=1 --exclude '*/pkg/lib/editor/static/build'
COPY --from=config-editor /build/static/build  /go/src/config-tool/pkg/lib/editor/static/build
RUN go install ./cmd/config-tool

# Final is the end container, where all the work from the other
# containers are copied in.
FROM base AS final
LABEL maintainer "thomasmckay@redhat.com"

# All of these chgrp+chmod commands are an Openshift-ism.
#
# Openshift runs a container as a random UID and GID 0, so anything
# that's in the base image and needs to be modified at runtime needs
# to make sure it's group-writable.
RUN alternatives --set python /usr/bin/python3
RUN set -ex\
	; setperms() { for d in "$@"; do chgrp -R 0 "$d" && chmod -R g=u "$d" && ls -ld "$d"; done; }\
	; newdir() { for d in "$@"; do mkdir -m g+w "$d" || { chgrp 0 "$d" && chmod g=u "$d"; }; ls -ld "$d"; done; }\
# Allow TLS certs to be created and installed as non-root user.
# See also update-ca-trust(8).
	; setperms /etc/pki/ca-trust/extracted /etc/pki/ca-trust/source/anchors\
# Allow for nginx to run unprivledged.
	; setperms /etc/nginx\
	; ln -sf /dev/stdout /var/log/nginx/access.log\
	; ln -sf /dev/stdout /var/log/nginx/error.log\
# Make a grip of runtime directories.
	; newdir /certificates /conf /conf/stack /datastorage\
# The code doesn't agree on where the configuration lives, so create a
# symlink.
	; ln -s $QUAYCONF /conf\
# Another Openshift-ism: it doesn't bother picking a uid that means
# anything to the OS inside the container, so the process needs
# permissions to modify the user database.
	; setperms /etc/passwd\
	;

WORKDIR $QUAYDIR
RUN mkdir ${QUAYDIR}/config_app
# Ordered from least changing to most changing.
COPY --from=jwtproxy /usr/local/bin/jwtproxy /usr/local/bin/jwtproxy
COPY --from=pushgateway /usr/local/bin/pushgateway /usr/local/bin/pushgateway
COPY --from=build-python /app /app
COPY --from=config-tool /go/bin/config-tool /bin
COPY --from=config-editor /build ${QUAYDIR}/config_app
COPY --from=build-static /build/static ${QUAYDIR}/static
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
