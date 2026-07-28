# OMR SQLite Migration Compatibility Contract

**Status:** Proposed implementation gate

**Scope:** Documentation-only Phase 0 for the Python-to-Go OMR SQLite handoff

**Immutable implementation evidence range:**
`c633fa301d9bf5e261ba072c673f7b2bc115e2e7..7565112cac0a02c839261a3b1a30cc756cdd0d1c`

**Frozen Python handoff:** `9fa37f66a9b6`

**External source revision eligible for support:** `3f8d7acdf7f9`

## Purpose

This document is the compatibility contract for migrating an OpenShift mirror
registry (OMR) v2.0.x SQLite database into the Go replacement. It freezes the
source boundary before migration behavior is changed.

This phase changes no runtime behavior. In particular, it does not add
fixtures, alter schema generation, change the migration allowlist, add a
migration dependency, or modify a database. Those changes may proceed only
after the gates in this document are met and reviewed.

## Normative language

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. A
revision being present in Alembic history or accepted by the current PR code is
not, by itself, evidence that it is a supported OMR source.

## Decisions

| ID | Decision |
| --- | --- |
| C1 | The analysis and patch-source range is immutable at `c633fa301d9b..7565112cac0a`. The existing PR #6351 branch is reference material, not the branch history for the replacement stack. |
| C2 | `3f8d7acdf7f9` is the only external OMR source revision eligible for support. Runtime support MUST remain gated until a faithful artifact-derived fixture confirms the revision and convergence contract. |
| C3 | The 23 other pre-root revisions accepted by PR #6351 are rejected as external sources. They have no demonstrated OMR v2.0.x release-head provenance. |
| C4 | Interrupted Python/Alembic revisions are not promised as migration inputs. Recovery MUST restore a verified backup or use a separately approved repair procedure for the exact failure shape. |
| C5 | The Python/Alembic compatibility layer ends at `9fa37f66a9b6`. Native Go revisions MUST use a separate ledger and MUST NOT advance `alembic_version` beyond `9fa37f66a9b6`. |
| C6 | Only `AUTHENTICATION_TYPE: Database` is eligible. External providers and malformed or missing provider values MUST be rejected during read-only preflight before OMR is stopped. |
| C7 | Databases stamped `a2fc72f380b7` are unsupported PR-development databases and are rejected by default. There is no permanent adoption path. |
| C8 | Migration is forward-only. Recovery is retry from a verified durable revision or restore from a verified backup, never a production schema downgrade. |

## Release provenance

### Method and confidence

The matrix below combines three authoritative records:

1. each published `quay/mirror-registry` v2.0.x release object's immutable tag
   and `.env`, which name the selected `quay-rhel8` image tag;
2. Red Hat Container Catalog tag history and image metadata, which identify the
   single build and manifest-list digest behind that tag; and
3. the matching public `quay/quay` v3.12.x source tag, whose Alembic graph has
   the single head `3f8d7acdf7f9`.

The image digest and image `vcs-ref` are direct catalog evidence (**high
confidence**). The Alembic head is currently derived from the corresponding
public source release tag rather than from a database run by the exact
protected image (**medium confidence**). A fixture generated from the exact
image digest MUST raise that last link to high confidence before runtime
support is enabled.

Evidence was rechecked on 2026-07-28. At that time the v3.12.0 through
v3.12.10 image tags each had one Container Catalog tag-history build. The
v3.12.18 tag-history endpoint was not yet populated; catalog image metadata
represented one manifest-list build with four architecture records. The
manifest-list digest, not an architecture-specific manifest digest, is recorded
below.

| OMR release | GitHub metadata | OMR tag commit | Quay image | Manifest-list digest | Image `vcs-ref` | Derived Alembic head | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v2.0.0 | Release | `73b8d86532e95a72ca4422f623a4d819433e2e79` | `quay-rhel8:v3.12.0` | `sha256:ad5dd877d2aed952ed69ed035981c6b90794157ce0dd199565792c1cd0a70833` | `15cda70139425872667bda96ae0fc8276bbdd063` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.1 | Release | `a648b719b6c605f442e7f38e8c79d7754a830e1b` | `quay-rhel8:v3.12.1` | `sha256:fbfb579f3329e29a5a1e27b5a61b2b9fb0d5589e7f2c256cc2b1296ea5e1f3ff` | `cb39b216a29f91aee8a5ebe77b0057a95d484cee` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.2 | Release | `fc7f7f5e8a55c02371693a3c74377ef5b39c2aec` | `quay-rhel8:v3.12.2` | `sha256:bbbe36c1fd7981bd0ab2d6f863f85489f8a246f17371863036ffe50d7097fce9` | `815e1ccc879a0d5334328d9e8686d8b4485c55a9` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.3 | Release | `32876ed0695ce51cf07adbfc46851e3a862b889e` | `quay-rhel8:v3.12.3` | `sha256:d2879e7d340010888f5e4f3e8239dd34f1c7d4361fcf2d9d0cac63664cbf7376` | `642c7c7c19c8b618704263f21939c7c08192a145` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.4 | Prerelease | `e609475d2eba1825866909d5d5997b048da5bc88` | `quay-rhel8:v3.12.4` | `sha256:91dc4228244565050246f151dab7518176724c71ec9e3d11e42b76f1fae6a6f8` | `c80991cdeb5c2280421338d1ac0c5f1bca07373d` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.5 | Prerelease | `862946d5934ff885b0df05df0590f8cbac153afa` | `quay-rhel8:v3.12.5` | `sha256:3c16ae3220afb54facdf5465090ab8423f8db86a66c3312d12d9f7714c5142b9` | `b0e5b40943cf6b752a6a82ae3c4504d1281a985b` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.6 | Prerelease | `3e2298049afc7e38d8212dc173b54599f4045e36` | `quay-rhel8:v3.12.8` | `sha256:39db593628b29251fd8cb54f90ec2b35a5397fa8fa5e6b414c376052bed884c6` | `ea8dd209e6af8d3f9e408d0c9dc000283ae21546` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.7 | Prerelease | `3f585d64b88a2bbd4ade07e7e130fb8a3c918361` | `quay-rhel8:v3.12.10` | `sha256:5c9c33b03cdff322498d40997bb9b4fe09e8b4dd80581ed315a9e79c1138eb09` | `d2dc978c266a7285e942fb63005fd46b4e20b993` | `3f8d7acdf7f9` | Medium pending fixture observation |
| v2.0.11 | Prerelease | `2b5757b738128b6534c42b9c6438451c87c2434b` | `quay-rhel8:v3.12.18` | `sha256:b6839e49202f29dd430cf53327061987737fedfe370d843b10434b203ef95755` | `27de798512e3c85335b8c687e281f2e581f905ea` | `3f8d7acdf7f9` | Medium pending fixture observation |

These are the nine published v2.0.x GitHub release objects found at the
evidence date. GitHub marks v2.0.4 through v2.0.7 and v2.0.11 as prereleases;
this contract includes their artifact states because they are publicly
installable and resolve to the same source revision. A `v2.0.10` Git tag exists,
but it has no published GitHub release or release assets and is not a source in
this contract.

All included OMR v2.0.x release objects therefore collapse to one candidate
external schema head. Patch releases remain separate manifest entries because their
artifacts and source commits differ. A single fixture MAY represent multiple
releases only after artifact-derived databases are shown to have identical
normalized schema, required seed data, and relevant auth rows.

The catalog `vcs-ref` values identify the Red Hat image builds but are not
objects in the public `quay/quay` repository. The matching public release tags
used to derive the Alembic head resolve as follows:

| Quay source tag | Public tag commit | Alembic head |
| --- | --- | --- |
| `v3.12.0` | `ae99470d5c67cafc831706b5b5d35670a6220524` | `3f8d7acdf7f9` |
| `v3.12.1` | `654d7bb5897d3dd6fb333373ea37842d894fcbee` | `3f8d7acdf7f9` |
| `v3.12.2` | `31f2e408bcb842a5bcba871d2f71387ce95d7180` | `3f8d7acdf7f9` |
| `v3.12.3` | `1eeea7a79d666df081b7745d6fd9c4506260e369` | `3f8d7acdf7f9` |
| `v3.12.4` | `3412c5b90cad82454b62e7473d76423ae32d5108` | `3f8d7acdf7f9` |
| `v3.12.5` | `48c5e5bf26efd8cdd84cc05d306eb54831690f45` | `3f8d7acdf7f9` |
| `v3.12.8` | `d0ce4cf18bc0024d96f822fc3faf0b8c75d40415` | `3f8d7acdf7f9` |
| `v3.12.10` | `1463ec2e35484ecfda7590d3a1334a40d3733571` | `3f8d7acdf7f9` |
| `v3.12.18` | `c08a6e688fa54f81a85b8dfe637831d3ba8f36ae` | `3f8d7acdf7f9` |

The online OMR package embeds a tag reference and can resolve it at install
time; the offline package embeds image contents at build time. A fixture MUST
record which package or digest produced it. The release tag alone is not enough.

## Source revision policy

### External OMR source

The source preflight allowlist is exactly:

```text
3f8d7acdf7f9
```

That revision is eligible because every included OMR v2.0.x release object maps
to a Quay 3.12.x line whose public source graph ends there. It MUST NOT be
activated in runtime code until the fixture gate below proves the exact
artifact-derived state and compatibility convergence.

The marker is necessary but not sufficient for a particular input. Before
source shutdown, read-only preflight MUST also establish:

- exactly one `alembic_version` row equal to `3f8d7acdf7f9`;
- a normalized source schema fingerprint matching an approved 3f8 fixture
  profile, including tables, columns, indexes, triggers, and foreign keys;
- required seed rows and source data invariants defined by that profile;
- successful `PRAGMA integrity_check` and `PRAGMA foreign_key_check`;
- detected OMR release/image provenance matching a matrix row, using source
  service/image metadata rather than trusting the database marker; and
- the authentication and key-continuity checks in this contract.

If source provenance is missing or conflicts with the structural profile,
preflight rejects the input as unsupported. A manually stamped or malformed
3f8 database is not accepted merely because its revision string matches.

### Rejected historical markers

PR #6351 currently accepts the following pre-root markers:

```text
0cdd1f27a450  0988213e0885  66147b81aad2  f67fe4871771
2664723e1b4b  8a7ba94c2e84  3f8d7acdf7f9  a32e17bfad20
5b8dc452f5c3  ba263f9be4a6  9085e82074f2  8e97c2cfee57
3634f2df3c5b  e8ed3fb547da  1623f40582ed  7078c84d14e8
9307c3d604b4  27d0df099ac4  a1b2c3d4e5f6  285f36ce97fd
b2c3d4e5f6a7  b1c2d3e4f5a6  15f06d00c4b3  414c5e2fc487
```

Only `3f8d7acdf7f9` is retained by this contract. The remaining 23 markers are
rejected because no OMR v2.0.x release in the provenance matrix shipped them as
a head and no product recovery promise has been established for them.

This narrowing also avoids claiming convergence through known gaps in the
current squash bridge. For sources predating the affected migrations, the
bridge does not account for all schema and required-data changes from
`0988213e0885`, `66147b81aad2`, `f67fe4871771`, `2664723e1b4b`, and
`8a7ba94c2e84`. Support MUST be removed rather than fabricated without release
provenance and faithful fixtures.

### Internal compatibility states

The following values are not external OMR source promises:

| Revision | Meaning | Policy |
| --- | --- | --- |
| `c3d4e5f6a7b8` | Synthetic squash/bridge root | MAY be recognized only as a durable state produced by the reviewed Go compatibility runner. |
| `b1a79fa8e630` | Mirrored Alembic transition | MAY be recognized only for exact retry of the reviewed runner. |
| `d064a4f00d4a` | Mirrored Alembic transition | MAY be recognized only for exact retry of the reviewed runner. |
| `b30800b1d271` | Mirrored Alembic transition | MAY be recognized only for exact retry of the reviewed runner. |
| `6715e4719375` | Mirrored Alembic transition | MAY be recognized only for exact retry of the reviewed runner. |
| `9fa37f66a9b6` | Frozen Python handoff | Compatibility no-op; proceed to the separate native ledger. |

Recognition of an internal state MUST require both its canonical schema/data
invariants and structured retry metadata atomically written by the reviewed Go
runner. That metadata MUST include a format version, runner build and contract
revision, source revision and source schema fingerprint, compatibility-plan
digest, last completed phase and durable revision, native version if present,
and verified backup path plus checksum. It MUST contain no secret values.

On retry, the runner validates the metadata against the selected target file,
its current revision, and the canonical structural/data profile for that exact
state. A missing, stale, plain-text, or mismatched marker is not proof of
ownership and MUST be rejected with recovery guidance. Finding one of these
revision values in an arbitrary source OMR database does not make it supported.
Missing, empty, multiple, unknown, or future Alembic revisions are rejected
without mutation.

### Interrupted Python upgrades

The Python Alembic environment configures online migrations with
`transactional_ddl=False`. SQLite DDL and version-marker durability across a
process or host failure therefore cannot be inferred safely from the marker
alone. An interruption may leave an intermediate marker, partially applied
schema, or both.

This contract does not promise to classify or repair those states. Restoring a
verified pre-upgrade backup is the only generally guaranteed recovery path.
After restore, the operator verifies source integrity and reruns the matching
OMR upgrade to its released head before Go migration preflight.

Finishing an upgrade in place is permitted only when that exact failure shape
has a separately reviewed OMR repair/resume procedure. Blindly rerunning
Alembic is not a general recovery path: an unguarded table or index may already
exist even though its revision marker was not committed. When no verified
backup or approved repair procedure exists, migration stops without mutation
and escalates for product support; it does not guess or back-stamp the state.

A future interrupted-upgrade route requires a separate product decision, an
exact state definition, an artifact-derived fault-reproduction fixture, and a
convergence test. It MUST NOT be added merely because the revision appears in
Alembic history.

## Frozen Python handoff

The compatibility target is exactly:

```text
PythonHandoffRevision = 9fa37f66a9b6
```

The generated SQLite DDL and seed data in the immutable PR head are stamped at
`9fa37f66a9b6`. The current `go-schema` target nevertheless runs `alembic
upgrade head`, so a later implementation phase MUST pin generation and drift
checks to this exact revision.

After compatibility conversion:

- `alembic_version` contains exactly one row equal to `9fa37f66a9b6`;
- native Go migration identifiers are recorded only in a separate numeric
  ledger;
- a newer Python head is rejected until this contract is explicitly revised;
  and
- schema generation moving to a newer Alembic head does not silently expand
  source compatibility.

`9fa37f66a9b6` is an ownership boundary, not evidence that OMR shipped that
revision.

## Authentication-provider policy

The Go config parser recognizes `Database`, `LDAP`, `JWT`, `Keystone`, `OIDC`,
and `AppToken`, but recognizing an enum is not migration support. At the
immutable PR head, runtime-config generation copies `AUTHENTICATION_TYPE` and
selected generic values but does not preserve provider-specific settings held
in the source config. Unknown Python config keys are collected in `Config.Extra`
and are not emitted into the generated runtime config. The migration path calls
`config.Load` but not `config.Validate`, so required generic secrets also need
an explicit preflight check.

The preflight policy is:

| Source `AUTHENTICATION_TYPE` | Decision | Reason |
| --- | --- | --- |
| `Database` | Eligible, subject to credential-continuity validation | The database remains the credential source and generic key material can be preserved and checked. |
| `LDAP` | Reject | LDAP server, bind, TLS, search, and mapping configuration is not migrated. |
| `JWT` | Reject | Provider-specific JWT verification and identity mapping configuration is not migrated. Registry bearer-token signing-key migration is a separate generic registry requirement and does not make this auth provider supported. |
| `Keystone` | Reject | Keystone endpoint, tenant/domain, TLS, and mapping configuration is not migrated. |
| `OIDC` | Reject | Issuer/client credentials, scopes, callbacks, and claim mapping are not migrated. |
| `AppToken` | Reject | Provider-specific configuration and end-to-end behavior are not established. This provider value is distinct from database-backed `$app` tokens. |
| Empty, unknown, or malformed | Reject | The installed registry would have no proven authentication path. |

For `Database`, read-only preflight MUST inspect the raw YAML before defaults
are applied and validate, without printing values:

- `AUTHENTICATION_TYPE` is explicitly present as a scalar and exactly
  `Database`; omission is rejected even though the target parser defaults it;
- `SERVER_HOSTNAME` is explicitly present or an explicit validated override is
  supplied;
- `SECRET_KEY` and `DATABASE_SECRET_KEY` are explicitly present, nonempty, and
  accepted by the target's Python-compatible key conversion/decoding helpers;
- every populated encrypted credential family that the target promises can be
  decrypted in memory with `DATABASE_SECRET_KEY`; plaintext is immediately
  discarded and never logged;
- the registry JWT signing key source is present and internally consistent;
- required TLS certificate/key material is present and valid when TLS is used;
  and
- the generated target config can represent the selected generic settings.

When no encrypted credential rows exist, key correctness cannot be proven by
decryption. The implementation still verifies byte-for-byte preservation of
both source keys in the generated target config before install.

The bridge MUST preserve password hashes, encrypted credential columns, and
token rows byte-for-byte unless a separately reviewed data migration requires a
change. This contract does not assert that every database-backed credential
kind is already implemented by the Go runtime; implementation phases MUST test
all credential kinds the product promises. Unsupported credential kinds are
not a reason to accept an external auth provider silently.

Supporting any rejected provider requires separate feature work that defines
all copied configuration keys, secret handling, target runtime behavior, and an
end-to-end authentication test. It is not part of the schema-runner redesign.

## Fixture provenance contract

Before `3f8d7acdf7f9` is enabled in runtime code, the repository MUST contain a
manifest and faithful immutable fixture evidence. Each manifest row records:

- OMR release and immutable OMR tag commit;
- online or offline package identity and checksum when used;
- exact Quay image reference and manifest-list digest;
- image architecture and architecture-specific manifest digest used to run the
  fixture;
- image `vcs-ref` and matching public source tag when available;
- observed `alembic_version` and whether it is a shipped head or a deliberately
  reproduced interrupted state;
- exact generation or extraction procedure, tool versions, and source URL;
- fixture path, byte size, SHA-256 checksum, and normalized schema fingerprint;
- required seed/data invariant fingerprint or explicit assertions; and
- product reason for retaining the source.

A faithful fixture is created or upgraded by the exact historical artifact. It
is not produced by changing `alembic_version` on a newer database, replaying a
handwritten approximation, or using current Python models against an old
marker.

The existing PR #6351 bridge test loads the synthetic
`internal/dal/dbcore/testdata/sqlite_c3d4e5f6a7b8_minimal.sql` fixture and
changes only its marker to `3f8d7acdf7f9`. That proves some idempotence against
the later c3-shaped schema; it does not prove convergence from a database
created by Quay 3.12.x. It MUST NOT be used as the compatibility fixture.

At least one exact artifact-derived fixture is required for each distinct
source schema/data state. Releases may share one checked-in fixture only after
separately generated artifact databases are shown equivalent under all
contract assertions. The manifest still retains one provenance row per
included release object.

Fixtures MUST contain no customer data, credentials, private keys, access
tokens, or release-registry credentials. Synthetic rows used to prove data
migration invariants MUST be documented and non-secret.

## `a2fc72f380b7` development databases

`a2fc72f380b7` is a Go-only tag-integrity marker introduced in the unshipped PR
#6351 range. It is not an Alembic release head and no OMR release in the matrix
contains it.

The permanent policy is to reject it. Developers recreate disposable databases
from the frozen `9fa37f66a9b6` handoff and the native ledger. The compatibility
chain MUST NOT treat `a2fc72f380b7` as Python ancestry.

If a maintainer identifies a specific non-disposable database produced by a
published PR-development build, preservation requires an optional, temporary,
separately reviewed adoption change. That change must verify the complete tag
schema and data invariant before atomically restoring
`alembic_version=9fa37f66a9b6` and recording native version 1. It must include
an owner and removal release. No such need is established by this contract.

## Implementation gates

No compatibility implementation PR may claim source support until all of the
following are true:

- [ ] A maintainer approves the external source set and auth policy in this
      document.
- [ ] An exact image-digest run observes `3f8d7acdf7f9` for every distinct
      release schema state.
- [ ] The provenance manifest and fixture checksums are reviewed.
- [ ] Every retained fixture converges to the `9fa37f66a9b6` canonical schema
      and required data invariants.
- [ ] Source preflight validates release/image provenance, the approved 3f8
      structural profile, required data, and integrity rather than trusting the
      revision marker alone.
- [ ] Database-auth preflight reads raw YAML key presence and proves promised
      encrypted credential families are decryptable without exposing values.
- [ ] Unsupported revisions and auth providers are rejected during read-only
      preflight before source shutdown, copy, or mutation.
- [ ] Retry uses structured, versioned, non-secret metadata and validates each
      internal revision against its canonical durable-state profile.
- [ ] Schema generation and drift checks are pinned to `9fa37f66a9b6`.
- [ ] Missing, multiple, unknown, future, malformed/back-stamped, stale-retry,
      and `a2fc72f380b7` states have explicit rejection tests.

## Non-goals for this phase

This document does not:

- add or generate a fixture;
- alter `knownOMRVersions` or any runtime compatibility path;
- change the Makefile or generated schema;
- add preflight behavior;
- repair bridge SQL;
- add a native migration ledger or Goose dependency;
- change tag behavior; or
- promise support for a future OMR, Python, or native revision.

## Evidence and reproduction

### Repository evidence in the immutable PR head

- `internal/dal/dbcore/bridge.go` contains the 24-entry pre-root allowlist.
- At the immutable base, `internal/dal/dbcore/migrate.go` defines
  `9fa37f66a9b6` as the Alembic target. At the immutable head it defines bridge
  root `c3d4e5f6a7b8` and the Go-only target `a2fc72f380b7`.
- `internal/dal/schema/sqlite/seed_data.sql` stamps the generated base at
  `9fa37f66a9b6`.
- `internal/dal/schema/sqlite/migrations/0002_*.sql` through `0006_*.sql` mirror
  the explicit compatibility path from `c3d4e5f6a7b8` to `9fa37f66a9b6`.
- `internal/dal/dbcore/bridge_test.go` back-stamps the later bridge fixture in
  `TestRunBridge_CreatesBridgeTables`.
- `internal/migrate/copy.go` emits only selected generic config fields.
- `internal/config/auth.go` validates the six provider enum values without
  defining provider-specific migration support; `internal/config/config.go`
  states that unknown keys in `Config.Extra` are not written back out.
- `data/users/__init__.py` consumes additional provider-specific LDAP, JWT,
  Keystone, AppToken, and OIDC settings that the target config does not model.
- `internal/config/validate_required.go` requires nonempty `SECRET_KEY` and
  `DATABASE_SECRET_KEY`, but `internal/migrate` does not invoke the full config
  validator.
- `data/migrations/env.py` sets `transactional_ddl=False` for online
  migrations.
- `Makefile` runs `alembic upgrade head` in `go-schema`.

Use immutable GitHub blob URLs rooted at
`7565112cac0a02c839261a3b1a30cc756cdd0d1c` when citing those files in review.

### Release-source checks

For each OMR tag, inspect its immutable image selection:

```bash
git -C /path/to/mirror-registry show v2.0.7:.env | grep '^QUAY_IMAGE='
git -C /path/to/mirror-registry rev-parse v2.0.7
```

The release pages are:

```text
https://github.com/quay/mirror-registry/releases/tag/v2.0.0
...
https://github.com/quay/mirror-registry/releases/tag/v2.0.7
https://github.com/quay/mirror-registry/releases/tag/v2.0.11
```

Red Hat Container Catalog exposes the image tag history at:

```text
https://catalog.redhat.com/api/containers/v1/tag-history/registry/
  registry.access.redhat.com/repository/quay/quay-rhel8/tag/<tag>
```

and image metadata, including manifest digests and `vcs-ref`, at:

```text
https://catalog.redhat.com/api/containers/v1/images
  ?filter=repositories.repository==quay/quay-rhel8
```

The corresponding public Quay source tags are `v3.12.0`, `v3.12.1`,
`v3.12.2`, `v3.12.3`, `v3.12.4`, `v3.12.5`, `v3.12.8`, `v3.12.10`, and
`v3.12.18`. Their migration graphs can be reproduced without executing migration code by
collecting each migration's `revision` and `down_revision`; each has the single
head `3f8d7acdf7f9`.
