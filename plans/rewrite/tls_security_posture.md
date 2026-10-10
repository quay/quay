# TLS and Security Posture Plan

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Define security-protocol posture for Go services, including TLS termination, cipher policy, digest strategy, and migration of multi-port behavior.

Primary source anchors:
- `conf/init/nginx_conf_create.py`
- `conf/nginx/nginx.conf.jnj`

## 2. Current-state compatibility requirements

1. Preserve ingress behavior for existing clients during migration.
2. Preserve proxy protocol behavior where configured.
3. Preserve HSTS and related security-header behavior.
4. Maintain support for required registry/API TLS versions during transition.

## 3. Termination model options

1. Keep nginx termination through M4 and migrate internals first.
2. Move to Go-native TLS termination with explicit compatibility validation.

Baseline recommendation:
- Option 1 for early milestones, with decision checkpoint before M4.

## 4. Cipher/protocol policy

- Transitional minimum: TLS 1.2 + TLS 1.3.
- Long-term target: TLS 1.3-preferred policy with explicit legacy exception list.
- Any cipher suite policy change requires compatibility report and rollback path.

## 5. Digest and algorithm evolution

- Preserve current digest/addressability behavior for existing content.
- Add explicit roadmap for SHA-512 support without changing existing digest contracts.
- Track post-quantum readiness as a design note (not a migration blocker).

## 6. Port/protocol mapping plan

Document and validate behavior for:
- external HTTPS/API port(s)
- registry port(s)
- internal service-to-service channels
- proxy-protocol-enabled listeners

## 7. Exit criteria

- Security posture approved by platform + security owners.
- TLS handshake compatibility tests pass for supported clients.
- Security regression checklist integrated into cutover go/no-go.
