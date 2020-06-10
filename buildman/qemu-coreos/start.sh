#!/bin/bash

VM_VOLUME_SIZE="${VM_VOLUME_SIZE:-32G}"
VM_MEMORY="${VM_MEMORY:-4G}"

set -e
set -x
set -o nounset

mkdir -p /userdata/openstack/latest
echo "${USERDATA}" > /userdata/openstack/latest/user_data

time qemu-img resize ./coreos_production_qemu_image.qcow2 "${VM_VOLUME_SIZE}"

qemu-system-x86_64 \
        -enable-kvm \
        -cpu host \
        -device virtio-9p-pci,fsdev=conf,mount_tag=config-2 \
        -nographic \
        -drive if=virtio,file=./coreos_production_qemu_image.qcow2 \
        -fsdev local,id=conf,security_model=none,readonly,path=/userdata \
        -m "${VM_MEMORY}" \
        -machine accel=kvm \
        -net nic,model=virtio \
        -net user,hostfwd=tcp::2222-:22 \
        -smp 2
