set -e
set -o nounset

TAG=${TAG:-"stable"}
IMAGE=${IMAGE:-"quay.io/quay/quay-builder-qemu-fedoracoreos"}
CLOUD_IMAGE=${CLOUD_IMAGE:-""}

if [ -z "$CLOUD_IMAGE" ]; then
    CHANNEL=${CHANNEL:-"stable"}
    CHANNEL_MANIFEST_JSON=`curl https://builds.coreos.fedoraproject.org/streams/stable.json`
    LOCATION=`echo $CHANNEL_MANIFEST_JSON | jq '.architectures.x86_64.artifacts.qemu.formats."qcow2.xz".disk.location' | tr -d '"'`
    VERSION=`echo $CHANNEL_MANIFEST_JSON | jq '.architectures.x86_64.artifacts.qemu.release' | tr -d '"'`

    time docker build --build-arg=channel=$CHANNEL --build-arg version=$VERSION --build-arg location=$LOCATION -t $IMAGE:$TAG .
else
    time docker build --build-arg=channel=$CHANNEL --build-arg version=$VERSION --build-arg location=$CLOUD_IMAGE -t $IMAGE:$TAG .
fi
