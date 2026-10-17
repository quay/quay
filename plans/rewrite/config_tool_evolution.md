# Config-Tool Co-Evolution Plan

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Ensure `config-tool/` (existing Go codebase) evolves with rewrite-era config contracts and migration switch controls.

## 2. Scope

- Keep validation compatibility for current Python-era configs.
- Add validation for rewrite switch namespace and owner controls.
- Add schema/versioning rules for new Go-only runtime settings.

## 3. Required additions

1. Validate owner-switch keys from `switch_spec.md`.
2. Validate transport settings from `switch_transport_design.md`.
3. Validate new service blocks for `registryd`, `api-service`, and Go workers.
4. Add compatibility warnings for deprecated Python-only settings.

## 4. Delivery and tests

- Add config fixtures for hybrid and go-only deployments.
- Add CI checks in config-tool pipeline for new schema revisions.
- Publish migration notes for operators using existing config templates.

## 5. Exit criteria

- Config-tool validates all rewrite-required settings.
- No rollout artifact depends on undocumented/unvalidated config fields.
