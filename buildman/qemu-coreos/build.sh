set -e
set -o nounset

TAG=${TAG:-"stable"}

CHANNEL=${CHANNEL:-"stable"}
CHANNEL_MANIFEST_JSON=`curl https://builds.coreos.fedoraproject.org/streams/stable.json`
LOCATION=`echo $CHANNEL_MANIFEST_JSON | jq '.architectures.x86_64.artifacts.qemu.formats."qcow2.xz".disk.location' | tr -d '"'`
VERSION=`echo $CHANNEL_MANIFEST_JSON | jq '.architectures.x86_64.artifacts.qemu.release' | tr -d '"'`

time docker build --build-arg=channel=$CHANNEL --build-arg version=$VERSION --build-arg location=$LOCATION -t quay.io/quay/quay-builder-qemu-fedoracoreos:$TAG .
