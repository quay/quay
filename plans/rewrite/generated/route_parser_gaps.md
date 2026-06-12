# Route Parser Gaps

Static inventory parsing left expression-based path templates unresolved for the routes below.

| Route ID | Source path template | Canonicalized path (planning) |
|---|---|---|
| `ROUTE-0284` | `/api/<'/v1/repository/<apirepopath:repository>/manifest/<regex("{0}"):manifestref>/pull_statistics'.format( digest_tools.DIGEST_PATTERN )>` | `/api/v1/repository/<apirepopath:repository>/manifest/<digest>/pull_statistics` |
| `ROUTE-0285` | `/api/<MANIFEST_DIGEST_ROUTE + "/labels">` | `/api/v1/repository/<apirepopath:repository>/manifest/<digest>/labels` |
| `ROUTE-0286` | `/api/<MANIFEST_DIGEST_ROUTE + "/labels">` | `/api/v1/repository/<apirepopath:repository>/manifest/<digest>/labels` |
| `ROUTE-0287` | `/api/<MANIFEST_DIGEST_ROUTE + "/labels/<labelid>">` | `/api/v1/repository/<apirepopath:repository>/manifest/<digest>/labels/<labelid>` |
| `ROUTE-0288` | `/api/<MANIFEST_DIGEST_ROUTE + "/labels/<labelid>">` | `/api/v1/repository/<apirepopath:repository>/manifest/<digest>/labels/<labelid>` |
| `ROUTE-0289` | `/api/<MANIFEST_DIGEST_ROUTE + "/security">` | `/api/v1/repository/<apirepopath:repository>/manifest/<digest>/security` |
| `ROUTE-0290` | `/api/<MANIFEST_DIGEST_ROUTE>` | `/api/v1/repository/<apirepopath:repository>/manifest/<digest>` |
| `ROUTE-0322` | `/v2/<MANIFEST_DIGEST_ROUTE>` | `/v2/<repopath:repository>/manifests/<digest>` |
| `ROUTE-0323` | `/v2/<MANIFEST_DIGEST_ROUTE>` | `/v2/<repopath:repository>/manifests/<digest>` |
| `ROUTE-0324` | `/v2/<MANIFEST_DIGEST_ROUTE>` | `/v2/<repopath:repository>/manifests/<digest>` |
| `ROUTE-0405` | `<app.config["LOCAL_OAUTH_HANDLER"]>` | `/oauth/localapp (default from config.LOCAL_OAUTH_HANDLER)` |

Action: keep these route IDs as explicit contract fixtures to avoid path-loss during migration.
