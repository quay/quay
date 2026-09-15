# Quay Web Playwright

## Service Suite

Service mode targets an already-running Quay deployment and only runs tests
tagged `@service-safe` by default. These tests must be read-only or otherwise
safe to run against shared deployments. Do not tag tests that create, update, or
delete organizations, repositories, tags, users, robot accounts, permissions,
messages, builds, or superuser settings.

Run the current service-safe subset against stage with:

```bash
QUAY_E2E_TARGET=stage pnpm run test:e2e:service
```

Run it against production with the required production guard:

```bash
QUAY_E2E_TARGET=prod \
QUAY_E2E_ALLOW_PROD=1 \
pnpm run test:e2e:service
```

Run it against another deployment with the original explicit URL overrides:

```bash
PLAYWRIGHT_BASE_URL=https://quay.example.test \
pnpm run test:e2e:service
```

Set `REACT_QUAY_APP_API_URL` as well when the API endpoint differs from the
frontend URL. Use `QUAY_E2E_TARGET=custom` when you want the target name to
reflect a non-stage/non-prod service.

Service mode intentionally:

- skips the local Playwright webserver build/deploy step
- skips global setup that creates fixed local users such as `admin`,
  `testuser`, and `readonly`
- filters to `@service-safe` unless `PLAYWRIGHT_GREP` is set
- uses one worker unless `PLAYWRIGHT_WORKERS` is set
- does not require or use superuser credentials

Additional service tags:

- `@service-safe`: default read-only checks expected to pass against shared
  stage and prod deployments
- `@service-integration`: read-only checks that require target-specific
  external dependencies or known public repositories
- `@service-mutating`: stage-only checks that create or delete disposable test
  data

Repository read checks can be pointed at a target-specific public image with:

```bash
QUAY_E2E_PUBLIC_REPOSITORY=<namespace/repository> \
QUAY_E2E_PUBLIC_TAG=<tag> \
PLAYWRIGHT_GREP=@service-integration \
PLAYWRIGHT_BASE_URL=https://quay.example.test \
pnpm run test:e2e:service
```

Optional regular-user credentials can be supplied for future authenticated
service tests:

```bash
QUAY_E2E_USERNAME=<username> \
QUAY_E2E_PASSWORD=<password> \
QUAY_E2E_TOKEN=<optional-token> \
QUAY_E2E_TARGET=stage \
pnpm run test:e2e:service
```

The initial service suite includes only unauthenticated/read-only smoke
coverage.
