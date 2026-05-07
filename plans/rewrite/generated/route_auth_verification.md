# Route Auth Verification

- total routes: 413
- manually verified routes (deep review): 7
- manually reviewed exception rows (closure pass): 45
- verified-source-anchored routes (manual + automation): 413
- unresolved auth routes: 0
- remaining manual signoff backlog: 0 rows (`route_auth_verification_checklist_summary.md`)

## Manually verified in this pass
- `ROUTE-0284` `GET` `/api/<'/v1/repository/<apirepopath:repository>/manifest/<regex("{0}"):manifestref>/pull_statistics'.format( digest_tools.DIGEST_PATTERN )>` -> `session-or-oauth2`
- `ROUTE-0285` `GET` `/api/<MANIFEST_DIGEST_ROUTE + "/labels">` -> `session-or-oauth2`
- `ROUTE-0286` `POST` `/api/<MANIFEST_DIGEST_ROUTE + "/labels">` -> `session-or-oauth2`
- `ROUTE-0287` `DELETE` `/api/<MANIFEST_DIGEST_ROUTE + "/labels/<labelid>">` -> `session-or-oauth2`
- `ROUTE-0288` `GET` `/api/<MANIFEST_DIGEST_ROUTE + "/labels/<labelid>">` -> `session-or-oauth2`
- `ROUTE-0289` `GET` `/api/<MANIFEST_DIGEST_ROUTE + "/security">` -> `anon-plus-psk-jwt-optional`
- `ROUTE-0290` `GET` `/api/<MANIFEST_DIGEST_ROUTE>` -> `session-or-oauth2`

## Automation

- Script: `plans/rewrite/scripts/route_auth_auto_verify.py`
- Latest report: `plans/rewrite/generated/route_auth_auto_verification_report.md`
