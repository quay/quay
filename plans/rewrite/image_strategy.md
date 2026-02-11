# Container Image Strategy

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Reduce runtime image complexity while preserving migration safety, multi-arch support, and FIPS requirements.

## 2. Current baseline concerns

- Current image includes Python, Node, nginx, supervisord, memcached, dnsmasq, skopeo, and multiple helper binaries.
- Migration target should converge toward smaller Go-centric runtime images.

## 3. Milestone image plan

| Milestone | Image composition goal |
|---|---|
| M0-M1 | Keep current Python image path; add Go sidecar/service images for canary capabilities |
| M2-M3 | Hybrid image set: registryd/api-service Go images + reduced Python fallback image |
| M4 | Worker-specific Go images for high-throughput workers; Python workers only where parity not complete |
| M5 | Go-first production images; Python image retained only for bounded emergency fallback window |

## 4. Component elimination roadmap

1. `supervisord` -> replace with explicit service orchestration (K8s/VM process model).
2. `nginx` -> optional retain vs Go-native TLS termination (see `tls_security_posture.md`).
3. `memcached`/`dnsmasq` -> retain only if still required by surviving compatibility path.
4. `skopeo` -> replace with Go-native `containers/image` integration (D-005 approved 2026-02-09); keep temporary fallback only during transition testing.

## 5. Multi-arch and FIPS constraints

- Required architectures: `x86_64`, `aarch64`, `ppc64le`, `s390x`.
- FIPS builds may require CGO/toolchain constraints; publish per-arch build matrix before M2.
- Do not mark an arch as supported in Go path until parity and FIPS smoke pass.

## 6. Exit criteria

- Per-milestone image BOM documented and signed off.
- CVE and base-image policy checks integrated in CI.
- Image-size trend tracked with explicit regression alerts.
