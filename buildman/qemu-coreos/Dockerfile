FROM centos:8 as executor-img
ARG location
ARG channel
ARG version

RUN [ -z "${location}" ] || [ -z "${channel}" ] || [ -z "${version}" ] && echo "ARG location, channel, version are required" && exit 1 || true

RUN echo "Downloading" ${location}
RUN curl -s -o coreos_production_qemu_image.qcow2.xz ${location} && unxz coreos_production_qemu_image.qcow2.xz


FROM centos:8
ARG location
ARG channel
ARG version

RUN yum -y update && \
  yum -y install openssh-clients qemu-kvm && \
  yum -y clean all

COPY --from=executor-img /coreos_production_qemu_image.qcow2 /coreos_production_qemu_image.qcow2
COPY start.sh /start.sh

LABEL com.coreos.channel ${channel}
LABEL com.coreos.version ${version}

ENTRYPOINT ["/bin/bash", "/start.sh"]
