FROM registry.access.redhat.com/ubi9/python-312-minimal:latest@sha256:c570170ec76987bb669de93a620f2f3b55b98e4121822c28140ec80da590c64d AS base
# Only set variables or install packages that need to end up in the
# final container here.
USER root

ENV PATH=/app/bin/:$PATH \
    PYTHON_VERSION=3.12 \
    PATH=$HOME/.local/bin/:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    CNB_STACK_ID=com.redhat.stacks.ubi9-python-312 \
    CNB_USER_ID=1001 \
    CNB_GROUP_ID=0 \
    PIP_NO_CACHE_DIR=off

ENV PYTHONUSERBASE=/app
ENV TZ=UTC
RUN set -ex\
	; microdnf -y module enable nginx:1.24 \
	; microdnf update -y \
	; microdnf -y --setopt=tsflags=nodocs install \
		dnsmasq \
		memcached \
		nginx \
		libpq-devel \
		libjpeg-turbo \
		openldap \
		openssl \
		python3-gpg \
    python3-six \
		skopeo \
		findutils \
	; microdnf -y reinstall tzdata \
	; microdnf -y clean all && rm -rf /var/cache/yum

# Build-python installs the requirements for the python code.
FROM base AS build-python
ENV PYTHONDONTWRITEBYTECODE=1
RUN set -ex\
	; microdnf -y --setopt=tsflags=nodocs install \
		gcc-c++ \
		git \
		openldap-devel \
		python3.12-devel \
		libffi-devel \
        openssl-devel \
        diffutils \
        file \
        make \
        libjpeg-turbo \
        libjpeg-turbo-devel \
		wget \
		rust-toolset \
		libxml2-devel \
		libxslt-devel \
		freetype-devel \
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

# Added below line for GRPC support for IBMZ i.e. s390x
ENV GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1

USER 1001

# Added GRPC support for IBM Power
# In Future if wget is to be removed , then uncomment below lines for grpc installation on IBM Power i.e. ppc64le
RUN ARCH=$(uname -m) ; echo $ARCH; \
    if [ "$ARCH" == "ppc64le" ] ; then \
    GRPC_LATEST=$(grep "grpcio" requirements.txt |cut -d "=" -f 3); \
	wget https://github.com/IBM/oss-ecosystem-grpc/releases/download/${GRPC_LATEST}/grpcio-${GRPC_LATEST}-cp312-cp312-linux_ppc64le.whl -O /tmp/grpcio-${GRPC_LATEST}-cp312-cp312-linux_ppc64le.whl; \
	python3 -m pip install --no-cache-dir /tmp/grpcio-${GRPC_LATEST}-cp312-cp312-linux_ppc64le.whl; \
	fi

RUN set -ex\
	; python3 -m pip install --no-cache-dir --progress-bar off $(grep -e '^pip=' -e '^wheel=' -e '^setuptools=' ./requirements.txt) \
	; python3 -m pip install --no-cache-dir --progress-bar off --requirement requirements.txt \
	;
RUN set -ex\
# Doing this is explicitly against the purpose and use of certifi.
	; for dir in\
		$(find "/opt/app-root/lib/python3.12/site-packages" -type d -name certifi)\
	; do chgrp -R 0 "$dir" && chmod -R g=u "$dir" ; done\
	;

# Build-static downloads the static javascript.
FROM registry.access.redhat.com/ubi9/nodejs-22-minimal@sha256:449f3e1b0a9c1ef766777ca84ea89bcc040a96d5f6d456c3a9acdd558dfc2b4f AS build-static
ARG BUILD_ANGULAR=true
WORKDIR /opt/app-root/src
# This below line is a workaround because in UBI 9, the OpenSSL version does not support MD4 anymore which is required by the combination of webpack and terser-webpack-plugin.
ENV NODE_OPTIONS=--openssl-legacy-provider
COPY --chown=1001:0 package.json package-lock.json  ./
RUN npm clean-install
COPY --chown=1001:0 static/  ./static/
COPY --chown=1001:0 *.json *.js  ./
RUN if [ "$BUILD_ANGULAR" = "true" ]; then npm run --quiet build; fi

# Build React UI
FROM registry.access.redhat.com/ubi9/nodejs-22-minimal:latest@sha256:449f3e1b0a9c1ef766777ca84ea89bcc040a96d5f6d456c3a9acdd558dfc2b4f AS build-ui
WORKDIR /opt/app-root
COPY --chown=1001:0 web/package.json web/package-lock.json  ./
RUN CYPRESS_INSTALL_BINARY=0 npm clean-install
COPY --chown=1001:0 web .
RUN npm run --quiet build

# Pushgateway grabs pushgateway.
FROM registry.access.redhat.com/ubi9/ubi-minimal:latest@sha256:bb08f2300cb8d12a7eb91dddf28ea63692b3ec99e7f0fa71a1b300f2756ea829 AS pushgateway
ENV OS=linux
ARG PUSHGATEWAY_VERSION=1.11.1
RUN set -ex\
	; microdnf update -y \
	; microdnf -y --setopt=tsflags=nodocs install tar gzip \
	; ARCH=$(uname -m) ; echo $ARCH \
	; if [ "$ARCH" == "x86_64" ] ; then ARCH="amd64" ; elif [ "$ARCH" == "aarch64" ] ; then ARCH="arm64" ; fi \
    ; TARBALL="pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}.tar.gz" \
    ; URL="https://github.com/prometheus/pushgateway/releases/download/v${PUSHGATEWAY_VERSION}/${TARBALL}" \
    ; curl -sSL ${URL} | tar xz  "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" \
    || tar -xzf /cachi2/output/deps/generic/${TARBALL} "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway"\
	; install "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" /usr/local/bin/pushgateway\
	;

# Config-tool builds the go binary in the configtool.
FROM registry.access.redhat.com/ubi9/go-toolset@sha256:82b82ecf4aedf67c4369849047c2680dba755fe57547bbb05eca211b22038e29 AS config-tool
WORKDIR /opt/app-root/src
COPY config-tool/ ./
ENV GOTOOLCHAIN=auto
RUN GOPATH=/opt/app-root/src/go GOFIPS140=latest go install -tags=fips ./cmd/config-tool

FROM registry.access.redhat.com/ubi9/ubi-minimal@sha256:bb08f2300cb8d12a7eb91dddf28ea63692b3ec99e7f0fa71a1b300f2756ea829 AS build-quaydir
WORKDIR /quaydir
COPY --from=build-static /opt/app-root/src/static /quaydir/static
COPY --from=build-ui /opt/app-root/dist /quaydir/static/patternfly

# Copy in source and update local copy of AWS IP Ranges.
# This is a bad place to do the curl, but there's no good place to do
# it except to have it checked in.
COPY --chown=0:0 . .
RUN set -ex\
	; chmod -R g=u ./conf\
    ; curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o util/ipresolver/aws-ip-ranges.json 2>/dev/null \
    || cp /cachi2/output/deps/generic/aws-ip-ranges.json util/ipresolver/aws-ip-ranges.json \
	;

# Final is the end container, where all the work from the other
# containers are copied in.
FROM base AS final
LABEL maintainer="quay-devel@redhat.com" \
      io.containers.capabilities="NET_BIND_SERVICE" \
      io.k8s.security.capabilities.drop="ALL" \
      io.k8s.security.capabilities.add="NET_BIND_SERVICE" \
      io.k8s.security.allow-privilege-escalation="false" \
      io.k8s.security.run-as-non-root="true"

ENV QUAYDIR=/quay-registry
ENV QUAYCONF=/quay-registry/conf
ENV QUAYRUN=/quay-registry/conf
ENV QUAYPATH=$QUAYDIR
ENV PYTHONPATH=$QUAYPATH

# All of these chgrp+chmod commands are an Openshift-ism.
#
# Openshift runs a container as a random UID and GID 0, so anything
# that's in the base image and needs to be modified at runtime needs
# to make sure it's group-writable.
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
# Harden /etc/passwd – no group write.
    ; chown root:root /etc/passwd \
    ; chmod 0644      /etc/passwd \
	; find /etc/pki/ -not -path '/etc/pki/entitlement*' -not -path '/etc/pki/consumer*' -exec chown 1001:0 {} + \
	; chown -R 1001:0 /etc/ssl/ \
	; chown -R 1001:0 /quay-registry \
	; chmod ug+w /etc/pki/ca-trust \
	; chmod ug+w -R /etc/pki/ca-trust/extracted /etc/pki/ca-trust/source/anchors \
	; find /etc/pki/ -not -path '/etc/pki/entitlement*' -not -path '/etc/pki/consumer*' -exec chmod ug+wx {} + \
	; chmod ug+wx -R /etc/ssl/


RUN python3 -m pip install --no-cache-dir --progress-bar off dumb-init

WORKDIR $QUAYDIR
# Ordered from least changing to most changing.
COPY --from=pushgateway /usr/local/bin/pushgateway /usr/local/bin/pushgateway
COPY --from=build-python /opt/app-root/lib/python3.12/site-packages /opt/app-root/lib/python3.12/site-packages
COPY --from=build-python /opt/app-root/bin /opt/app-root/bin
COPY --from=config-tool /opt/app-root/src/go/bin/config-tool /bin
COPY --from=build-quaydir /quaydir $QUAYDIR

# Strip setuid/setgid bits — with allowPrivilegeEscalation: false these are
# inert at runtime; removing them reduces scanner noise and attack surface.
RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

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
