#!/bin/bash
# RPM-lock install smoke test. It is not a replay of the Konflux build.
#   arch:    the lock's arch sections match rpms.in.yaml's arches.
#   fetch:   Hermeto downloads every locked RPM, checks size and checksum, and
#            generates a local repo from them (fetch-deps + inject-files).
#   install: rpms.in.yaml's modules and packages install offline with microdnf
#            from that x86_64 repo, with GPG checks, in rpms.in.yaml's context
#            image.
# The lockfile is only read, never regenerated.
#
# Usage: hack/validate-rpm-lock.sh [LOCKFILE]   (default: rpms.lock.yaml)
# Needs podman.
set -euo pipefail

# hermeto 0.61.0, from prefetch-dependencies-oci-ta 0.10.1 bundle
HERMETO_IMAGE="quay.io/konflux-ci/hermeto@sha256:43596c6351cdf7188b09fd4dcf5c6b3bb8b57ea557e84a1aa624f60e74c624ce"
# The prefetch task's output mount point (KBC_PD_OUTPUT_DIR_MOUNT_POINT).
OUT_DIR="/cachi2/output"

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
import sys, yaml
spec = yaml.safe_load(open("/src/rpms.in.yaml"))
want = sorted(spec["arches"])
got = sorted(a["arch"] for a in yaml.safe_load(open("/src/rpms.lock.yaml"))["arches"])
if got != want:
    sys.exit(f"STAGE arch: FAILED lock arches {got} != rpms.in.yaml arches {want}")
print(spec["context"]["image"])
print(" ".join(spec.get("moduleEnable", [])))
print(" ".join(spec["packages"]))
')"
echo "STAGE arch: ok"
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
if "$ENGINE" run --rm --network=none --platform linux/amd64 \
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
