FROM debian:latest as executor-img
ARG location
ARG channel
ARG version

RUN [ -z "${location}" ] || [ -z "${channel}" ] || [ -z "${version}" ] && echo "ARG location, channel, version are required" && exit 1 || true
RUN apt-get clean && apt-get update && apt-get upgrade -y
RUN apt-get install -y \
  xz-utils \
  curl

RUN echo "Downloading" ${location}
RUN curl -s -o coreos_production_qemu_image.qcow2.xz ${location} && unxz coreos_production_qemu_image.qcow2.xz


FROM debian:latest
ARG location
ARG channel
ARG version

RUN apt-get clean && apt-get update && apt-get upgrade -y && \
  apt-get install -y \
  openssh-client \
  qemu-kvm && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=executor-img /coreos_production_qemu_image.qcow2 /coreos_production_qemu_image.qcow2
COPY start.sh /start.sh

LABEL com.coreos.channel ${channel}
LABEL com.coreos.version ${version}

ENTRYPOINT ["/bin/bash", "/start.sh"]
