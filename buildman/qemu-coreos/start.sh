#!/bin/bash

VM_VOLUME_SIZE="${VM_VOLUME_SIZE:-32G}"
VM_MEMORY="${VM_MEMORY:-4G}"

set -e
set -x
set -o nounset

echo "${USERDATA}" > /userdata/user_data

time qemu-img resize --shrink /userdata/coreos_production_qemu_image.qcow2 "${VM_VOLUME_SIZE}"

/usr/libexec/qemu-kvm \
        -enable-kvm \
        -cpu host \
        -nographic \
        -drive if=virtio,file=/userdata/coreos_production_qemu_image.qcow2 \
        -fw_cfg name=opt/com.coreos/config,file=/userdata/user_data \
        -m "${VM_MEMORY}" \
        -machine accel=kvm \
        -net nic,model=virtio \
        -net user,hostfwd=tcp::2222-:22 \
        -smp 2
