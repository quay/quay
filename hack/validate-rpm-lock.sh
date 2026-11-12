#!/bin/bash
# Validate an RPM lockfile the way the Konflux hermetic build consumes it:
#   fetch:   Hermeto downloads every locked RPM, checks size and checksum, and
#            generates a local repo from them.
#   install: rpms.in.yaml's modules and packages install offline from that repo,
#            with GPG checks, in rpms.in.yaml's context image.
# The lockfile is only read, never regenerated.
#
# Usage: hack/validate-rpm-lock.sh [LOCKFILE]   (default: rpms.lock.yaml)
# Needs podman.
set -euo pipefail

# hermeto 0.64.0
HERMETO_IMAGE="quay.io/konflux-ci/hermeto@sha256:3c7a8622981aec970c159e608500d75a01e6bb42564ec25a92369e178b6ace8f"
OUT_DIR="/tmp/hermeto-output"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$(realpath "${1:-$ROOT/rpms.lock.yaml}")"
ENGINE="$(command -v podman || true)"
: "${ENGINE:?podman is required}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir "$WORK/src" "$WORK/out"
cp "$LOCK" "$WORK/src/rpms.lock.yaml"
cp "$ROOT/rpms.in.yaml" "$WORK/src/rpms.in.yaml"

# Hermeto's own Python has PyYAML, so the host needs nothing beyond the engine.
INPUT="$("$ENGINE" run --rm -v "$WORK/src:/src:z" --entrypoint /venv/bin/python "$HERMETO_IMAGE" -c '
import yaml
spec = yaml.safe_load(open("/src/rpms.in.yaml"))
print(spec["context"]["image"])
print(" ".join(spec.get("moduleEnable", [])))
print(" ".join(spec["packages"]))
')"
IMAGE="$(sed -n 1p <<<"$INPUT")"
MODULES="$(sed -n 2p <<<"$INPUT")"
PACKAGES="$(sed -n 3p <<<"$INPUT")"

echo "== fetch: $LOCK"
if "$ENGINE" run --rm -v "$WORK/src:/src:z" -v "$WORK/out:/out:z" "$HERMETO_IMAGE" \
        fetch-deps --source /src --output /out '{"type": "rpm", "path": "."}' &&
    "$ENGINE" run --rm -v "$WORK/out:/out:z" "$HERMETO_IMAGE" \
        inject-files /out --for-output-dir "$OUT_DIR"; then
    echo "STAGE fetch: ok"
else
    echo "STAGE fetch: FAILED"
    exit 1
fi

echo "== install: $IMAGE, modules: $MODULES"
# The generated x86_64 repo file replaces the image's repos.d, so nothing can
# come from the network or from an unlocked repo.
if "$ENGINE" run --rm --network=none \
        -v "$WORK/out:$OUT_DIR:z" \
        -v "$WORK/out/deps/rpm/x86_64/repos.d:/etc/yum.repos.d:z" \
        -e MODULES="$MODULES" -e PACKAGES="$PACKAGES" \
        "$IMAGE" sh -euc '
            repos="$(cat /etc/yum.repos.d/*.repo | grep -c "^\[" || true)"
            checked="$(cat /etc/yum.repos.d/*.repo | grep -Ec "^gpgcheck *= *1 *$" || true)"
            if [ "$repos" -eq 0 ] || [ "$repos" -ne "$checked" ]; then
                echo "gpgcheck=1 on $checked of $repos repos"
                exit 1
            fi
            test -s /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
            rpm -q gpg-pubkey
            for module in $MODULES; do
                microdnf -y module enable "$module"
            done
            microdnf -y --setopt=tsflags=nodocs install $PACKAGES
        '; then
    echo "STAGE install: ok"
else
    echo "STAGE install: FAILED"
    exit 1
fi
