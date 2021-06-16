#!/bin/bash

VM_VOLUME_SIZE="${VM_VOLUME_SIZE:-32G}"
VM_MEMORY="${VM_MEMORY:-4G}"

set -e
set -x
set -o nounset

echo "${USERDATA}" > /userdata/user_data

MIN_IMAGE_SIZE_BYTES=$(qemu-img info coreos_production_qemu_image.qcow2 | grep "virtual size" | cut -d " " -f 5 | tr -d "()")
VM_VOLUME_SIZE_BYTES=$(numfmt --from=iec $VM_VOLUME_SIZE)

if [ "$VM_VOLUME_SIZE_BYTES" -gt "$MIN_IMAGE_SIZE_BYTES" ]
then
    time qemu-img resize /userdata/coreos_production_qemu_image.qcow2 "${VM_VOLUME_SIZE}" || echo "Failed to resize VM image. Check VM_VOLUME_SIZE"
fi

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
