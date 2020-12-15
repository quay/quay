FROM centos:8

ENV OS=linux \
    ARCH=amd64 \
    PYTHON_VERSION=3.6 \
    PATH=$HOME/.local/bin/:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# source code will be mounted here.
ENV QUAYDIR /quay-registry 
WORKDIR $QUAYDIR

# all files necessary to invoke quay-entrypoint in the
# local-dev environment will exist here.
ENV QUAYCONF /quay-registry/local-dev
ENV QUAYPATH "."

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


ENV JWTPROXY_VERSION=0.0.3
RUN curl -fsSL -o /usr/local/bin/jwtproxy "https://github.com/coreos/jwtproxy/releases/download/v${JWTPROXY_VERSION}/jwtproxy-${OS}-${ARCH}" && \
    chmod +x /usr/local/bin/jwtproxy

ENV PUSHGATEWAY_VERSION=1.0.0
RUN curl -fsSL "https://github.com/prometheus/pushgateway/releases/download/v${PUSHGATEWAY_VERSION}/pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}.tar.gz" | \
    tar xz "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" && \
    mv "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}/pushgateway" /usr/local/bin/pushgateway && \
    rm -rf "pushgateway-${PUSHGATEWAY_VERSION}.${OS}-${ARCH}" && \
    chmod +x /usr/local/bin/pushgateway

RUN curl -L -o /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.2/dumb-init_1.2.2_amd64
RUN chmod +x /usr/local/bin/dumb-init

# keep this last, will allow for fastest container rebuilds.
COPY requirements.txt .
RUN alternatives --set python /usr/bin/python3 && \
    python -m pip install --no-cache-dir --upgrade setuptools pip && \
    python -m pip install --no-cache-dir -r requirements.txt --no-cache && \
    python -m pip freeze

EXPOSE 8080 8443 7443 9091 55443

ENTRYPOINT ["dumb-init", "--", "/quay-registry/quay-entrypoint.sh"]
CMD ["registry"]
