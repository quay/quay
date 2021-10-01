
###################
FROM registry.centos.org/centos/centos:8 as config-editor

# Switch to CentOS Stream
RUN dnf install centos-release-stream -y
RUN dnf swap centos-{linux,stream}-repos -y
RUN dnf distro-sync -y
RUN dnf upgrade -y

WORKDIR /config-editor

RUN INSTALL_PKGS="\
    git \
    " && \
    yum -y --setopt=tsflags=nodocs --setopt=skip_missing_names_on_install=False install $INSTALL_PKGS

RUN git clone https://github.com/quay/config-tool.git /config-editor && \
    cp -R pkg/lib/editor/* .
RUN yum install -y nodejs && \
    npm install --ignore-engines && \
    npm run build


###################
FROM golang:1.15 as config-tool

WORKDIR /go/src/config-tool
RUN git clone https://github.com/quay/config-tool.git /go/src/config-tool
RUN rm -rf /go/src/config-tool/pkg/lib/editor/static/build
COPY --from=config-editor /config-editor/static/build  /go/src/config-tool/pkg/lib/editor/static/build

RUN go install ./cmd/config-tool


###################
FROM registry.centos.org/centos/centos:8

LABEL maintainer "thomasmckay@redhat.com"

ENV OS=linux \
    ARCH=amd64 \
    PYTHON_VERSION=3.6 \
    PATH=$HOME/.local/bin/:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

ENV QUAYDIR /quay-registry
ENV QUAYCONF /quay-registry/conf
ENV QUAYPATH "."

# Switch to CentOS Stream
RUN dnf install centos-release-stream -y
RUN dnf swap centos-{linux,stream}-repos -y
RUN dnf distro-sync -y
RUN dnf upgrade -y

RUN mkdir $QUAYDIR
WORKDIR $QUAYDIR

COPY --from=config-tool /go/bin/config-tool /bin
RUN mkdir ${QUAYDIR}/config_app
COPY --from=config-editor /config-editor ${QUAYDIR}/config_app


RUN INSTALL_PKGS="\
    python3 \
    nginx \
    openldap \
    gcc-c++ git \
    openldap-devel \
    python3-devel \
    python3-gpg \
    dnsmasq \
    memcached \
    nodejs \
    openssl \
    skopeo \
    " && \
    yum -y --setopt=tsflags=nodocs --setopt=skip_missing_names_on_install=False install $INSTALL_PKGS && \
    yum -y update && \
    yum -y clean all

COPY . .

RUN alternatives --set python /usr/bin/python3 && \
    python -m pip install --no-cache-dir --upgrade setuptools pip && \
    python -m pip install --no-cache-dir -r requirements.txt --no-cache && \
    python -m pip freeze


RUN mkdir -p $QUAYDIR/static/webfonts && \
    mkdir -p $QUAYDIR/static/fonts && \
    mkdir -p $QUAYDIR/static/ldn && \
    PYTHONPATH=$QUAYPATH python -m external_libraries && \
    npm install --ignore-engines && \
    npm run build


ENV JWTPROXY_VERSION=0.0.3
RUN curl -fsSL -o /usr/local/bin/jwtproxy "https://github.com/coreos/jwtproxy/releases/download/v${JWTPROXY_VERSION}/jwtproxy-${OS}-${ARCH}" && \
    chmod +x /usr/local/bin/jwtproxy

ENV PUSHGATEWAY_VERSION=1.4.0
RUN curl -fsSL "https://github.com/prometheus/pushgateway/releases/download/v${PUSHGATEWAY_VERSION}/pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}.tar.gz" | \
    tar xz "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" && \
    mv "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" /usr/local/bin/pushgateway && \
    rm -rf "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}" && \
    chmod +x /usr/local/bin/pushgateway

# Update local copy of AWS IP Ranges.
RUN curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o util/ipresolver/aws-ip-ranges.json

RUN ln -s $QUAYCONF /conf && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stdout /var/log/nginx/error.log && \
    chmod -R a+rwx /var/log/nginx

# Cleanup
RUN UNINSTALL_PKGS="\
    gcc-c++ git \
    openldap-devel \
    gpgme-devel \
    python3-devel \
    optipng \
    kernel-headers \
    " && \
    yum remove -y $UNINSTALL_PKGS && \
    yum clean all && \
    rm -rf /var/cache/yum /tmp/* /var/tmp/* /root/.cache

EXPOSE 8080 8443 7443 9091 55443

RUN chgrp -R 0 $QUAYDIR && \
    chmod -R g=u $QUAYDIR

RUN mkdir /datastorage && chgrp 0 /datastorage && chmod g=u /datastorage && \
    chgrp 0 /var/log/nginx && chmod g=u /var/log/nginx && \
    mkdir -p /conf/stack && chgrp 0 /conf/stack && chmod g=u /conf/stack && \
    mkdir -p /tmp && chgrp 0 /tmp && chmod g=u /tmp && \
    mkdir /certificates && chgrp 0 /certificates && chmod g=u /certificates && \
    chmod g=u /etc/passwd


# Allow TLS certs to be created and installed as non-root user
RUN chgrp -R 0 /etc/pki/ca-trust/extracted && \
    chmod -R g=u /etc/pki/ca-trust/extracted && \
    chgrp -R 0 /etc/pki/ca-trust/source/anchors && \
    chmod -R g=u /etc/pki/ca-trust/source/anchors && \
    chgrp -R 0 /usr/local/lib/python$PYTHON_VERSION/site-packages/certifi && \
    chmod -R g=u /usr/local/lib/python$PYTHON_VERSION/site-packages/certifi

VOLUME ["/var/log", "/datastorage", "/tmp", "/conf/stack"]

USER 1001

ENTRYPOINT ["dumb-init", "--", "/quay-registry/quay-entrypoint.sh"]
CMD ["registry"]
