# Garbage Collection Patterns

Concurrency and FK cleanup patterns for Go registry GC. Read this before
working on any GC, blob lifecycle, or storage deletion code in the Go
registry rewrite (`internal/gc/`, `internal/oci/`).

These patterns were extracted from bugs found during the initial GC
implementation (PR #6318) that required 14 days of rework. Each pattern
addresses a specific class of failure that static analysis and AI-assisted
code generation missed.

## 1. FK Cascade Ordering

**Rule:** Always delete dependent rows before parent rows in GC operations.

The registry schema has FK relationships that prevent deleting a parent
row while dependent rows still reference it. GC must delete dependents
first, within the same transaction as the parent delete.

### Tag deletion

Delete `tagnotificationsuccess` rows before the `tag` row:

```
tagnotificationsuccess (tag_id → tag.id)  ←  delete first
tag                                        ←  delete second
```

See `SQLiteStore.DeleteExpiredTags` in `internal/gc/sqlite_store.go`:
`DeleteTagNotifications` runs before `DeleteExpiredTag` inside one
transaction.

### Manifest deletion

Delete all dependent rows before the `manifest` row:

```
manifestlabel          (manifest_id → manifest.id)    ←  delete first
manifestchild          (manifest_id, child_manifest_id)
manifestblob           (manifest_id → manifest.id)
manifestsecuritystatus (manifest_id → manifest.id)
tag                    (manifest_id → manifest.id)
manifest                                               ←  delete last
```

See `SQLiteStore.DeleteManifest` in `internal/gc/sqlite_store.go`.

### Blob (imagestorage) deletion

Delete all dependent rows before the `imagestorage` row:

```
uploadedblob           (blob_id → imagestorage.id)          ←  delete first
imagestorageplacement  (storage_id → imagestorage.id)
imagestoragesignature  (storage_id → imagestorage.id)
imagestorage                                                 ←  delete last
```

See `deleteBlobRows` in `internal/gc/sqlite_store.go`.

### Python reference

The Python GC in `data/model/gc.py` (`_garbage_collect_manifest`) and
`data/model/storage.py` (`garbage_collect_storage`) follows the same FK
ordering. When adding new FK-dependent tables, check both codebases.

## 2. Defense-in-Depth Blob Protection

**Rule:** Blob creation must atomically register both the blob record and
its upload protection marker. GC must revalidate orphan status inside the
delete transaction.

### The race condition

If blob upload (PutBlob) and protection registration (PutUploadedBlob)
are separate transactions, a GC cycle can run between them:

```
Upload goroutine          GC goroutine
─────────────────         ─────────────────
PutBlob (tx1 commits)
                          FindOrphanedBlobs → finds new blob (no protection)
                          DeleteBlobRecord → deletes it
PutUploadedBlob (tx2)
  → blob is gone, upload silently lost
```

This caused 40 test failures during soak testing of PR #6318.

### The fix: atomic registration

`PutRepositoryBlob` (called from `blobStore.recordBlob` in
`internal/registry/distribution/middleware/blob.go`) creates the
`imagestorage` row and the `uploadedblob` protection marker in a single
transaction. GC cannot see the blob without its protection.

### The fix: revalidation before delete

`SQLiteStore.DeleteBlobRecord` revalidates each candidate inside the
delete transaction:

1. Re-reads the blob row and checks that `content_checksum` and
   `image_size` still match the candidate (detects concurrent mutation).
2. Calls `blobIsProtected` to check for `manifestblob` and active
   `uploadedblob` references.
3. Only proceeds with deletion if both checks pass.

See `DeleteBlobRecord`, `readBlobCandidate`, and `blobIsProtected` in
`internal/gc/sqlite_store.go`.

### Checklist for new blob lifecycle code

- Never split blob record creation and protection registration into
  separate transactions.
- If adding a new protection mechanism (beyond `uploadedblob`), add a
  corresponding check in `blobIsProtected`.
- If changing `FindOrphanedBlobs`, ensure the query excludes all
  protection markers, not just `manifestblob`.

## 3. DB-Filesystem Coordination via BlobLockSet

**Rule:** When GC deletes both metadata and physical storage for a blob,
hold a per-digest lock across both operations. Upload paths must acquire
the same lock.

### The race condition

Even with correct DB-level protection, a race exists between GC's storage
deletion and a concurrent upload of the same digest:

```
Upload goroutine              GC goroutine
─────────────────             ─────────────────
                              DeleteBlobRecord (tx commits)
                                → DB row gone, DeleteFromStorage=true
PutBlob → writes file to disk
PutRepositoryBlob (tx commits)
  → DB row exists, blob protected
                              blobs.Delete(digest)
                                → physical file deleted
  → DB points to missing file
```

GC's DB revalidation passed (the blob was orphaned at check time), but
the physical delete races with a concurrent upload writing the same file.

### The fix: BlobLockSet

`BlobLockSet` (`internal/oci/blob_locker.go`) provides in-process
per-digest mutual exclusion. Both GC and upload paths acquire the lock
for the blob's digest:

**GC side** (`collector.collectBlob` in `internal/gc/sqlite_collector.go`):

```go
unlock, err := c.locker.Lock(ctx, dgst)
if err != nil { return ... }
defer unlock()

result, err := c.store.DeleteBlobRecord(ctx, candidate)
// ... if result.DeleteFromStorage:
c.blobs.Delete(ctx, deleteDigest)
```

The lock is held across both `DeleteBlobRecord` (DB) and `blobs.Delete`
(filesystem).

**Upload side** (`blobStore.Put` and `blobWriter.Commit` in
`internal/registry/distribution/middleware/blob.go`):

```go
unlock, err := bs.repo.locker.Lock(ctx, expected)
if err != nil { return ... }
defer unlock()

desc, err := bs.BlobStore.Put(ctx, mediaType, p)
// ... recordBlob(ctx, desc)
```

The lock is held across both the filesystem write and the DB registration.

### Limitation

`BlobLockSet` is in-process only. Deployments with multiple registry
processes sharing one storage directory need cross-process locking (e.g.,
distributed locks via Redis). The Python registry uses `GlobalLock` with
Redis for this purpose (see `data/model/storage.py`,
`garbage_collect_storage`).

### Checklist for new storage operations

- Any code that writes or deletes blob files must acquire the
  `BlobLocker` for the digest first.
- The lock must be held across both the filesystem operation and the
  corresponding DB mutation.
- If adding a new upload path (e.g., cross-repo mount, resumable upload
  commit), ensure it acquires the `BlobLocker`.

## 4. Shared-Checksum Safety

**Rule:** Before deleting physical storage files, check
`CountBlobsByChecksum` to confirm no other `imagestorage` row shares the
same `content_checksum`.

Multiple `imagestorage` rows can share the same `content_checksum` (e.g.,
the same layer pushed to different repositories). Deleting the physical
file when other rows still reference it causes data loss.

### Implementation

In `SQLiteStore.DeleteBlobRecord` (`internal/gc/sqlite_store.go`):

```go
if checksum.Valid {
    count, err := q.CountBlobsByChecksum(ctx, checksum)
    // ...
    result.DeleteFromStorage = count == 0
}
```

The `CountBlobsByChecksum` query (`internal/dal/queries/gc.sql`) runs
inside the same transaction as the blob row deletion, so the count
reflects the state after the current row is gone.

The collector (`sqlite_collector.go`) only calls `blobs.Delete` when
`result.DeleteFromStorage` is true.

### Python reference

The Python GC in `data/model/storage.py` (`garbage_collect_storage`)
performs the same check via `placements_to_filtered_paths_set`, which
queries `ImageStorage` for remaining rows with the same
`content_checksum` before adding a path to the removal list.

## 5. Cross-Reference Python GC

**Rule:** When implementing Go equivalents of Python Quay features,
always read the Python implementation first to identify FK relationships,
safety checks, and edge cases.

### Key Python GC files

| File | What it covers |
|------|----------------|
| `data/model/gc.py` | Tag expiry, manifest collection, BFS manifest-tree walk, label cleanup |
| `data/model/storage.py` | Blob orphan detection, FK-dependent row cleanup (`ImageStoragePlacement`, `ImageStorageSignature`), shared-checksum filtering, `GlobalLock` for storage deletion |
| `data/model/oci/tag.py` | `lookup_unrecoverable_tags` (grace period logic) |
| `data/model/blob.py` | `lookup_expired_uploaded_blobs` |
| `data/model/notification.py` | `delete_tag_notifications_for_tag` |

### Key Go GC files

| File | What it covers |
|------|----------------|
| `internal/gc/gc.go` | `Collector` interface, `Stats`, `Config` |
| `internal/gc/store.go` | `Store` interface, domain types |
| `internal/gc/sqlite_store.go` | SQLite `Store` with FK cleanup and transactions |
| `internal/gc/sqlite_collector.go` | Four-phase collector (orchestration only) |
| `internal/gc/worker.go` | Background goroutine with panic recovery |
| `internal/oci/blob_locker.go` | `BlobLockSet` per-digest coordination |
| `internal/dal/queries/gc.sql` | sqlc queries for orphan detection and FK cleanup |
| `internal/registry/distribution/middleware/blob.go` | Upload-side blob registration and locking |

### What to check

When porting or extending GC behavior:

1. Read the Python function that handles the equivalent operation.
2. Identify all FK-dependent tables it cleans up.
3. Verify the Go implementation deletes the same dependent rows.
4. Check for safety mechanisms (revalidation, locking, shared-checksum
   checks) and ensure the Go equivalent has them.
5. Look for edge cases in the Python tests (`test/test_gc.py`) that may
   not be covered by the Go tests yet.

## Four-Phase GC Algorithm

For reference, the Go GC runs four phases on each cycle (every 30s by
default):

1. **Clean expired upload markers** -- removes `uploadedblob` rows past
   their 1-hour expiry.
2. **Expire tags** -- deletes tags whose `lifetime_end_ms` plus the
   namespace's `removed_tag_expiration_s` grace period has elapsed.
   Deletes `tagnotificationsuccess` first (FK).
3. **Collect orphaned manifests** -- iteratively deletes manifests with
   no tags, no `manifestchild` parents (global), and no `subject`
   referrers (global). Iterative BFS handles manifest list cascades
   (max 100 iterations).
4. **Collect orphaned blobs** -- revalidates each candidate inside a
   transaction, deletes FK-dependent rows, checks
   `CountBlobsByChecksum`, then deletes physical storage under the
   `BlobLockSet` digest lock. Also cleans stale upload directories
   older than 48 hours.

See `collector.Collect` in `internal/gc/sqlite_collector.go`.
