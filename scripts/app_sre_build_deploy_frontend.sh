#!/bin/bash
# Local build script for front ends
# This script is used to build the front end locally
# Use this to test the frontend build system locally when making changes

# Usage:
# 3. Change the IMAGE var at the top of this script to the value from build_deploy.sh
# 3. Run the script
# 4. Run the container podman run -p 8000:8000 localhost/edge:5316bd7
# 5. Open the app in your browser at http://localhost:8000/apps/edge 
#
# Note: You can find the image name and tag by looking at the output of the script
# or by running `podman images`. Also, fill in the app name in the URL with the 
# app you are testing

# --------------------------------------------
# Export vars for helper scripts to use
# --------------------------------------------

set -exv
CURRENT_DIR=$(dirname $0)
FRONTEND_DIR=$CURRENT_DIR/web

# Move to the frontend directory
cd $PWD/web

mkdir -p workspace
export WORKSPACE=$(pwd)

export BASE_IMG="quayio-frontend"
export IMG="${BASE_IMG}:latest"
export BACKUP_BASE_IMG="quayio-frontend-backup"
export BACKUP_IMAGE="${BACKUP_URL}/${BACKUP_BASE_IMG}"


export APP_NAME=$(node -e "console.log(require(\"${WORKSPACE:-.}${APP_DIR:-}/package.json\").insights.appname)")
export CONTAINER_NAME="$APP_NAME"
# main IMAGE var is exported from the pr_check.sh parent file
export IMAGE="quay.io/app-sre/quayio-frontend"
export IMAGE_TAG=$(git rev-parse --short=7 HEAD)
export IS_PR=false

export CI_ROOT=$WORKSPACE/workspace
export NPM_BUILD_SCRIPT="build-plugin"

# HACK: Save old Dockerfiles because the container needs to generate it's own
mv .dockerignore .dockerignore.bak
mv Dockerfile Dockerfile.bak

# NOTE: Make sure this volume is mounted 'ro', otherwise Jenkins cannot clean up the
# workspace due to file permission errors; the Z is used for SELinux workarounds
# -e NODE_BUILD_VERSION can be used to specify a version other than 12
docker run -it --name $CONTAINER_NAME \
  -v $PWD:/workspace:ro,Z \
  -e APP_DIR=$APP_DIR \
  -e IS_PR=$IS_PR \
  -e CI_ROOT=$CI_ROOT \
  -e NODE_BUILD_VERSION=$NODE_BUILD_VERSION \
  -e SERVER_NAME=$SERVER_NAME \
  -e NPM_BUILD_SCRIPT \
  quay.io/cloudservices/frontend-build-container:d8b1dfc

TEST_RESULT=$?

if [ $TEST_RESULT -ne 0 ]; then
  echo "Test failure observed; aborting"
  exit 1
fi

# Extract files needed to build contianer
mkdir -p $WORKSPACE/build
docker cp $CONTAINER_NAME:/container_workspace/ $WORKSPACE/build
cd $WORKSPACE/build/container_workspace/ && export APP_ROOT="$WORKSPACE/build/container_workspace/"

docker build -t "${IMAGE}:${IMAGE_TAG}" $APP_ROOT -f $APP_ROOT/Dockerfile
docker rm $CONTAINER_NAME

# Restore Dockerfiles
mv .dockerignore.bak .dockerignore
mv Dockerfile.bak Dockerfile

# save the image as a tar archive
docker save ${IMAGE}:${IMAGE_TAG} -o ${BASE_IMG}

# push image to backup repository
# skopeo copy --dest-creds "${BACKUP_USER}:${BACKUP_TOKEN}" \
#     "docker-archive:${BASE_IMG}" \
#     "docker://${BACKUP_IMAGE}:latest"
# 
# skopeo copy --dest-creds "${BACKUP_USER}:${BACKUP_TOKEN}" \
#     "docker-archive:${BASE_IMG}" \
#     "docker://${BACKUP_IMAGE}:${IMAGE_TAG}"

# push to quay.io repository
#
skopeo copy --dest-creds "${QUAY_USER}:${QUAY_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${IMAGE}:latest"

skopeo copy --dest-creds "${QUAY_USER}:${QUAY_TOKEN}" \
    "docker-archive:${BASE_IMG}" \
    "docker://${IMAGE}:${IMAGE_TAG}"

# remove the archived image
rm ${BASE_IMG}
