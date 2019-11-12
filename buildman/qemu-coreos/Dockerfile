FROM debian

RUN apt-get clean && apt-get update && apt-get upgrade -y # 03APR2017
RUN apt-get install -y \
  bzip2 \
  curl \
  openssh-client \
  qemu-kvm

ARG channel=stable
ARG version=current

RUN echo "Downloading http://${channel}.release.core-os.net/amd64-usr/${version}/coreos_production_qemu_image.img.bz2"
RUN curl -s -O http://${channel}.release.core-os.net/amd64-usr/${version}/coreos_production_qemu_image.img.bz2 && \
  bzip2 -d coreos_production_qemu_image.img.bz2

RUN apt-get remove -y curl bzip2 && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY start.sh /start.sh

LABEL com.coreos.channel ${channel}
LABEL com.coreos.version ${version}

ENTRYPOINT ["/bin/bash", "/start.sh"]
