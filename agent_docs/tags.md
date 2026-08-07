# Tag & Manifest Lifecycle

Documentation for the tag/manifest subsystem in `data/model/oci/tag.py`.
Read this before modifying any code that creates, deletes, expires, retargets,
or prunes tags.

## Tag/Manifest Relationship Model

A **manifest** is a content-addressed object (identified by `sha256:...` digest)
stored once per repository. A **tag** is a mutable, user-facing name alias that
points to a manifest.

**Key invariant: multiple tags can alias the same manifest.** Deleting or
expiring one tag does not mean the manifest is unreferenced — other alive tags
may still point to it.

### Schema (from `data/database.py`)

```
Manifest
  repository    FK → Repository
  digest        unique per (repository, digest)
  media_type    FK → MediaType
  manifest_bytes
  subject       nullable (OCI referrers)
  ...

Tag
  name                  e.g. "latest", "v1.0", "sha256-abc123...64hex.sig"
  repository            FK → Repository
  manifest              FK → Manifest
  lifetime_start_ms     creation timestamp (epoch ms)
  lifetime_end_ms       expiration timestamp (epoch ms), NULL = never expires
  immutable             boolean, default False
  hidden                boolean, default False (hidden tags excluded from listings)
  reversion             boolean, tag was reverted to a prior manifest
  tag_kind              FK → TagKind enum
  linked_tag            self-FK (tag aliasing, rarely used)
```

### Tag Lifecycle States

A tag is **alive** when:
```python
(lifetime_end_ms IS NULL) OR (lifetime_end_ms > now_ms)
```
and `hidden == False`.

A tag is **expired** when `lifetime_end_ms <= now_ms`.

A tag is **unrecoverable** when it is expired AND past the namespace's
time-machine window (`Namespace.removed_tag_expiration_s`). Unrecoverable
tags are candidates for garbage collection.

### Unique Constraint

The index `(repository, name, lifetime_end_ms)` is **unique**. This prevents
deadlocks during concurrent tag move and delete operations. When expiring
multiple tags with the same name, each must have a distinct `lifetime_end_ms`
(use an incrementing offset — see `remove_tag_from_timemachine`).

## Cosign Tag Schema

Cosign tags encode a manifest digest in the tag name to associate signatures,
attestations, and SBOMs with their subject manifest.

### Naming Convention

Pattern: `sha256-<64-lowercase-hex-chars>.<suffix>`

Regex: `^sha256-[a-f0-9]{64}\.(sig|att|sbom)$`

Constants in `data/model/oci/tag.py`:
```python
COSIGN_TAG_SCHEMA_PATTERN = r"^sha256-[a-f0-9]{64}\.(sig|att|sbom)$"
COSIGN_TAG_SCHEMA_RE = re.compile(COSIGN_TAG_SCHEMA_PATTERN)
COSIGN_TAG_SCHEMA_PREFIX = "sha256-"
COSIGN_TAG_SCHEMA_DIGEST_LEN = 64
COSIGN_TAG_SCHEMA_SUFFIXES = ("sig", "att", "sbom")
```

### How Cosign Tags Relate to Subject Manifests

Given a manifest with digest `sha256:abcdef...` (64 hex chars), the Cosign
signature tag name is `sha256-abcdef....sig` (colon replaced with dash).

The tag's `manifest` FK points to the **signature manifest** (which contains
the actual signature data), not to the subject manifest. The relationship to
the subject is encoded only in the tag name.

### Cosign vs OCI Referrers

Cosign tags are an older, tag-based mechanism for associating signatures with
manifests. OCI 1.1 introduced a referrers API (`Manifest.subject` field) that
achieves the same goal without special tag names. Quay supports both. Cosign
tags are visible in tag listings; OCI referrers use hidden temporary tags.

### SQL Matching Without REGEXP

`_not_cosign_tag_schema_clause(model=Tag)` provides a SQLite-safe SQL clause
that matches the Cosign pattern using `SUBSTR` and `LENGTH` instead of
`REGEXP`. It accepts a Tag model or alias so it can be used in subqueries:

```python
OtherTag = Tag.alias()
query.where(_not_cosign_tag_schema_clause(OtherTag))
```

`is_cosign_tag_schema(tag_name)` is the Python-side equivalent for checking
a tag name string.

## Tag Mutation Paths and Invariants

Every code path that modifies tag state must maintain a set of invariants.
Failure to do so causes data inconsistencies that are not self-healing.

### Mutation Functions

| Function | What it does | Location |
|----------|-------------|----------|
| `retarget_tag` | Creates or moves a tag to point at a new manifest | `data/model/oci/tag.py` |
| `_delete_tag` | Expires a single tag (sets `lifetime_end_ms`) | `data/model/oci/tag.py` |
| `delete_tag` | Public entry point: looks up alive tag, checks immutability, calls `_delete_tag` | `data/model/oci/tag.py` |
| `delete_tags_for_manifest` | Expires all alive tags pointing to a manifest | `data/model/oci/tag.py` |
| `set_tag_end_ms` | Sets expiration timestamp on a tag | `data/model/oci/tag.py` |
| `change_tag_expiration` | Changes tag expiration with min/max bounds | `data/model/oci/tag.py` |
| `remove_tag_from_timemachine` | Pushes tag expiry outside the time-machine window for immediate GC | `data/model/oci/tag.py` |
| `set_tag_immutable` | Toggles the immutable flag on a tag | `data/model/oci/tag.py` |
| `set_tags_immutability_for_manifest` | Sets immutability on all alive tags for a manifest | `data/model/oci/tag.py` |
| `fetch_paginated_autoprune_repo_tags_by_number` | Fetches tags eligible for number-based autopruning | `data/model/oci/tag.py` |
| `fetch_paginated_autoprune_repo_tags_older_than_ms` | Fetches tags eligible for age-based autopruning | `data/model/oci/tag.py` |
| `_expire_cosign_sibling_tags` | Expires Cosign sibling tags when a subject manifest is dereferenced | `data/model/oci/tag.py` |

### Invariant 1: Cosign Sibling Cascade on Manifest Dereference

**Rule:** When the last alive, non-Cosign tag referencing a manifest is
removed, all Cosign sibling tags for that manifest's digest must also be
expired.

**Why:** Autoprune excludes Cosign-schema tag names (see Autoprune section
below). If Cosign tags are not cleaned up when their subject is dereferenced,
they persist forever as orphans.

**Implementation:** `_expire_cosign_sibling_tags` performs this cleanup. It:
1. Computes Cosign tag names from the manifest digest
2. Filters to alive, mutable tags matching those names
3. When `subject_manifest` is provided, includes a `NOT EXISTS` subquery to
   verify no other alive, non-Cosign tag still references the same manifest
4. Expires matching tags by setting `lifetime_end_ms = now_ms`

**Where it must be called:**
- `_delete_tag` — calls it when `expire_cosign=True` (default) and the tag
  is not itself a Cosign tag
- `delete_tags_for_manifest` — calls it once after all tags on the manifest
  are deleted, with `expire_cosign=False` on individual `_delete_tag` calls
  to avoid redundant cascades
- `retarget_tag` — calls it for the **displaced** manifest when a tag is
  moved to point at a different manifest, but only when the displaced
  manifest differs from the new target manifest

**Common mistake (Premature cascade):** Calling `_expire_cosign_sibling_tags`
without the `subject_manifest` parameter (or without checking for remaining
alive aliases) will expire Cosign tags even when another tag still references
the same manifest. Always pass `subject_manifest` to enable the `NOT EXISTS`
guard.

### Invariant 2: Immutability Guard on All Mutations

**Rule:** If `features.IMMUTABLE_TAGS` is enabled and `tag.immutable` is
`True`, the tag must not be deleted, expired, overwritten, or retargeted.

**Implementation:**
- `delete_tag` checks `tag.immutable` before calling `_delete_tag`
- `delete_tags_for_manifest` checks all tags for immutability before deleting any
- `retarget_tag` checks the existing tag's immutability before displacing it
- `_expire_cosign_sibling_tags` includes `Tag.immutable == False` in its
  WHERE clause
- `remove_tag_from_timemachine` checks immutability for alive tags
- `lookup_unrecoverable_tags` excludes immutable tags from GC candidates
  when `FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE` is False
- `find_repository_with_garbage` skips immutable tags in candidate selection

**Common mistake (Immutable bypass):** Adding a new tag mutation path
(e.g., a new expiration function or a cleanup worker) without checking
`tag.immutable`. Every function that modifies `lifetime_end_ms` or deletes
a tag must gate on immutability.

### Invariant 3: Transaction Boundary Requirements

**Rule:** All reads that inform a mutation decision and the mutation itself
must occur inside the same `db_transaction()` block. Queries outside the
transaction create TOCTOU (time-of-check/time-of-use) races.

**Implementation:**
- `retarget_tag` wraps the existing-tag lookup, expiration, and new tag
  creation in a single `db_transaction()`, with an advisory lock to
  serialize concurrent mutations per repository
- `_delete_tag` wraps statistics cleanup, notification cleanup, tag
  expiration, and Cosign cascade in a single `db_transaction()`
- `delete_tags_for_manifest` reads alive tags and processes all deletions
  inside one `db_transaction()`

**Advisory locks:** `retarget_tag` acquires a repository-scoped advisory lock
(`db_advisory_xact_lock`) to serialize tag mutations. This prevents races
where two concurrent pushes both read the existing tag, both create a new tag,
and one of the new tags is immediately orphaned:

```python
with db_transaction():
    lock_id = compute_advisory_lock_id("retarget_tag", manifest.repository_id)
    db_advisory_xact_lock(lock_id)
    # ... read existing tag, expire it, create new tag ...
```

Advisory locks are released when the transaction commits/rolls back. They do
not block unrelated reads (unlike `SELECT FOR UPDATE` on the Repository row).

**Common mistake (TOCTOU race):** Executing `Tag.select()` before opening
`db_transaction()`, then using the result inside the transaction. A concurrent
tag creation between the SELECT and the transaction boundary will be missed.

### Invariant 4: Retarget Must Clean Up Displaced Manifests

**Rule:** When `retarget_tag` moves a tag from manifest A to manifest B,
Cosign sibling tags for manifest A must be expired if no other alive tag
references manifest A.

**Why:** Autoprune excludes Cosign-schema names, so orphaned Cosign tags for
manifest A would persist forever.

**Implementation:** `retarget_tag` calls `_expire_cosign_sibling_tags` on
the displaced manifest when `displaced_manifest.id != manifest.id` (i.e.,
the tag is actually moving to a different manifest, not being recreated on
the same one).

### Invariant 5: Optimistic Update for Concurrent Safety

**Rule:** Tag mutations must use optimistic locking by including the expected
current value of `lifetime_end_ms` in the UPDATE's WHERE clause.

**Implementation:**
```python
updated = (
    Tag.update(lifetime_end_ms=now_ms)
    .where(Tag.id == tag.id, Tag.lifetime_end_ms == tag.lifetime_end_ms)
    .execute()
)
if updated != 1:
    return None  # concurrent modification detected
```

This pattern appears in `_delete_tag`, `set_tag_end_ms`, and
`remove_tag_from_timemachine`. If `updated != 1`, the tag was modified by
another process and the operation should be treated as failed.

## Peewee ORM Pitfalls in Tag Operations

### `Query.where()` Returns a New Query

Peewee's `.where()` is **not** in-place — it returns a new query object:

```python
# WRONG — original query is unmodified
query = Tag.select().where(Tag.repository == repo_id)
query.where(Tag.hidden == False)  # result is discarded!

# CORRECT
query = Tag.select().where(Tag.repository == repo_id)
query = query.where(Tag.hidden == False)
```

### `LIKE` Case Sensitivity Differs by Database

`LIKE` is case-insensitive on SQLite but case-sensitive on PostgreSQL. For
case-insensitive searching, use `Tag.name.contains()` (which uses `LIKE` with
wildcards) and be aware of the behavior difference in tests (SQLite) vs
production (PostgreSQL).

Cosign tag matching deliberately uses `SUBSTR` equality instead of `LIKE` to
ensure case-sensitive matching on both databases.

### `IS NULL` Syntax

Peewee uses the `>>` operator for `IS NULL` checks:

```python
Tag.lifetime_end_ms >> None     # IS NULL
~(Tag.lifetime_end_ms >> None)  # IS NOT NULL
```

The alive-tag filter pattern:
```python
(Tag.lifetime_end_ms >> None) | (Tag.lifetime_end_ms > now_ms)
```

### Tag Alias Queries

When writing subqueries that reference Tag in both the outer query and the
subquery, use `Tag.alias()` to avoid column name collisions:

```python
OtherTag = Tag.alias()
subquery = OtherTag.select(1).where(
    OtherTag.repository == repository_id,
    OtherTag.manifest == subject_manifest,
    ...
)
```

### `fn.EXISTS` for Subquery Guards

Use `fn.EXISTS(subquery)` and `~fn.EXISTS(subquery)` for NOT EXISTS:

```python
conditions.append(~fn.EXISTS(other_alive))
```

## Autoprune Subsystem

Autoprune automatically expires tags based on namespace or repository policies.
The system deliberately excludes certain tag types from pruning.

### Autoprune Tag Queries

Two functions fetch tags eligible for pruning:

- `fetch_paginated_autoprune_repo_tags_by_number` — returns alive tags
  beyond a maximum count, ordered by `lifetime_start_ms DESC` (newest first,
  so oldest tags are pruned)
- `fetch_paginated_autoprune_repo_tags_older_than_ms` — returns alive tags
  older than a specified age

### Tags Excluded from Autoprune

Both autoprune queries apply these exclusion filters:

```python
Tag.hidden == False,           # exclude hidden/temporary tags
Tag.immutable == False,        # exclude immutable tags
_not_cosign_tag_schema_clause(),  # exclude Cosign-schema tag names
```

**Why Cosign tags are excluded:** Cosign tags are metadata (signatures,
attestations, SBOMs) attached to a subject manifest. Pruning them independently
would remove security signatures while the signed image remains available.
Cosign tags should only be cleaned up via cascade when their subject manifest
is dereferenced (see Invariant 1).

**Consequence:** Because autoprune never touches Cosign tags, any code path
that removes a tag without performing Cosign cascade cleanup will leave orphan
Cosign tags that persist indefinitely. This is why every mutation path must
maintain Invariant 1.

### Autoprune Policies

Policies are defined at two levels:
- **Namespace-level** (`NamespaceAutoPrunePolicy`): applies to all
  repositories in the namespace
- **Repository-level** (`RepositoryAutoPrunePolicy`): applies to a single
  repository

Policy methods:
- `number_of_tags` — keep at most N tags, prune the oldest
- `creation_date` — prune tags older than a time duration

Policies support optional `tag_pattern` (regex) and `tag_pattern_matches`
(boolean) fields to further filter which tags are eligible for pruning.

### Autoprune Worker

The `workers/autopruneworker.py` worker runs periodically, fetches repositories
with active autoprune policies, and calls the tag query functions above to
identify and expire eligible tags.

## Garbage Collection

Tags feed into the garbage collection pipeline. The GC worker
(`workers/gc/`) identifies repositories with unrecoverable tags and cleans
up their manifests and blobs.

### GC-Relevant Functions

- `find_repository_with_garbage` — finds a repository with expired tags
  past the time-machine window; excludes immutable tags when
  `FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE` is False
- `lookup_unrecoverable_tags` — returns tags that are expired and past
  their namespace's `removed_tag_expiration_s` window

### Time Machine

The time machine allows recovery of recently deleted tags. Each namespace
has a `removed_tag_expiration_s` setting that controls how long expired tags
remain recoverable. Tags are only eligible for GC after this window passes.

`remove_tag_from_timemachine` pushes a tag's expiry outside the time-machine
window to make it immediately eligible for GC.

## Checklist for New Tag Mutation Code

When adding or modifying any code that changes tag state, verify:

- [ ] **Cosign cascade**: Does the code call `_expire_cosign_sibling_tags`
  when the last non-Cosign alive tag on a manifest is removed? Pass
  `subject_manifest` to enable the NOT EXISTS guard.
- [ ] **Immutability**: Does the code check `features.IMMUTABLE_TAGS` and
  `tag.immutable` before modifying the tag? Is `Tag.immutable == False`
  included in any bulk UPDATE WHERE clauses?
- [ ] **Transaction boundary**: Are all reads and writes inside the same
  `db_transaction()` block? No queries outside the transaction that inform
  decisions inside it?
- [ ] **Optimistic locking**: Does the UPDATE include
  `Tag.lifetime_end_ms == tag.lifetime_end_ms` to detect concurrent
  modifications?
- [ ] **Unique constraint**: If expiring multiple tags with the same name,
  does each get a distinct `lifetime_end_ms` value?

## Key Files

| File | Purpose |
|------|---------|
| `data/model/oci/tag.py` | All tag query and mutation functions |
| `data/database.py` | Tag, Manifest, ManifestChild model definitions |
| `data/model/immutability.py` | Immutability policy evaluation |
| `data/model/autoprune.py` | Autoprune policy CRUD and configuration |
| `data/registry_model/registry_oci_model.py` | Registry abstraction calling tag functions |
| `workers/autopruneworker.py` | Autoprune worker that executes pruning policies |
| `workers/gc/` | Garbage collection workers |
