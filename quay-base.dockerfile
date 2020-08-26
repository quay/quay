# vim:ft=dockerfile

FROM phusion/baseimage:0.10.0

ENV OS linux
ENV ARCH amd64
ENV DEBIAN_FRONTEND noninteractive
ENV HOME /root
ENV QUAYDIR /quay-registry
ENV QUAYCONF /quay-registry/conf
ENV QUAYPATH "."

RUN mkdir $QUAYDIR
WORKDIR $QUAYDIR

# This is so we don't break http golang/go#17066
# When Ubuntu has nginx >= 1.11.0 we can switch back.
RUN  add-apt-repository ppa:nginx/development

# Add Yarn repository until it is officially added to Ubuntu
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
# Install system packages
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
     dnsmasq           \
     g++               \
     gdb               \
     gdebi-core        \
     git               \
     jpegoptim         \
     libevent-2.0.5    \
     libevent-dev      \
     libffi-dev        \
     libfreetype6-dev  \
     libgpgme11        \
     libgpgme11-dev    \
     libjpeg62         \
     libjpeg62-dev     \
     libjpeg8          \
     libldap-2.4-2     \
     libldap2-dev      \
     libmagic1         \
     libpq-dev         \
     libpq5            \
     libsasl2-dev      \
     libsasl2-modules  \
     memcached         \
     nginx             \
     nodejs            \
     optipng           \
     openssl           \
     python-dbg        \
     python-dev        \
     python-pip        \
     python-virtualenv \
     yarn=0.22.0-1     \
     w3m # 27MAR2018

# Install cfssl
RUN mkdir /gocode
ENV GOPATH /gocode
RUN curl -O https://storage.googleapis.com/golang/go1.10.linux-amd64.tar.gz && \
    tar -xvf go1.10.linux-amd64.tar.gz && \
    mv go /usr/local && \
    rm -rf go1.10.linux-amd64.tar.gz && \
    /usr/local/go/bin/go get -u github.com/cloudflare/cfssl/cmd/cfssl && \
    /usr/local/go/bin/go get -u github.com/cloudflare/cfssl/cmd/cfssljson && \
    cp /gocode/bin/cfssljson /bin/cfssljson && \
    cp /gocode/bin/cfssl /bin/cfssl && \
    rm -rf /gocode && rm -rf /usr/local/go

# Install jwtproxy
ENV JWTPROXY_VERSION=0.0.3
RUN curl -fsSL -o /usr/local/bin/jwtproxy https://github.com/coreos/jwtproxy/releases/download/v$(JWTPROXY_VERSION)/jwtproxy-$(OS)-$(ARCH) && \
    chmod +x /usr/local/bin/jwtproxy

# Install pushgateway
ENV PUSHGATEWAY_VERSION=1.0.0
RUN curl -fsSL https://github.com/prometheus/pushgateway/releases/download/$(PUSHGATEWAY_VERSION)/pushgateway-$(PUSHGATEWAY_VERSION).$(OS)-$(ARCH).tar.gz | \
    tar xz pushgateway-$(PUSHGATEWAY_VERSION).$(OS)-$(ARCH)/pushgateway && \
    mv pushgateway-$(PUSHGATEWAY_VERSION).$(OS)-$(ARCH)/pushgateway /usr/local/bin/pushgateway && \
    rm -rf pushgateway-$(PUSHGATEWAY_VERSION).$(OS)-$(ARCH) && \
    chmod +x /usr/local/bin/pushgateway

# Install python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN virtualenv --distribute venv \
    && venv/bin/pip install --no-cache-dir -r requirements.txt \
    && venv/bin/pip install --no-cache-dir -r requirements-dev.txt \
    && venv/bin/pip freeze

# Install front-end dependencies
COPY static/ package.json tsconfig.json webpack.config.js tslint.json yarn.lock ./
RUN yarn install --ignore-engines


RUN mkdir -p /etc/my_init.d /etc/systlog-ng /usr/local/bin $QUAYDIR/static/fonts $QUAYDIR/static/ldn /usr/local/nginx/logs/

COPY external_libraries.py _init.py ./

RUN venv/bin/python -m external_libraries

RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache
VOLUME ["/var/log", "/datastorage", "/tmp"]

RUN mkdir scripts
ADD scripts/detect-config.sh scripts/.
RUN ./scripts/detect-config.sh
EXPOSE 443 8443 80
