# Fix Plan: Clair Not Triggered to Rescan After Proxy Cache Completes

## Bug Summary

**Issue**: After pulling all layers of an image through Quay's proxy cache, Clair is not triggered to rescan the image. The manifest remains in "unsupported" status instead of being scanned for vulnerabilities.

**Impact**: Users relying on Quay proxy cache for upstream registries cannot get vulnerability reports for cached images, severely limiting the security scanning capability of proxy-cached repositories.

**Current Workaround**: Manually delete manifestsecuritystatus records where index_status = -2:
```sql
DELETE FROM manifestsecuritystatus WHERE index_status = -2;
```

## Root Cause Analysis

### The Problem Flow

1. **Initial Manifest Pull (Proxy Cache)**
   - User pulls an image through Quay configured as a proxy cache
   - Proxy cache creates the manifest in the database (`registry_proxy_model.py:_create_manifest_and_retarget_tag`)
   - Placeholder blobs are created (ImageStorage records without ImageStoragePlacement)
   - Blob download jobs are queued for background processing (`registry_proxy_model.py:699-727`)

2. **Security Worker Attempts to Scan**
   - Security worker picks up the new manifest for scanning (`securityworker.py:_index_in_scanner`)
   - Calls `registry_model.list_manifest_layers()` to get layer information
   - Since blobs are placeholders (no ImageStoragePlacement), `list_manifest_layers()` returns None or empty
   - Security worker marks manifest as `MANIFEST_UNSUPPORTED` with `index_status = -2` (`secscan_v4_model.py:390-401`)

3. **Background Blob Download**
   - ProxyCacheBlobWorker processes queued blob download jobs (`proxycacheblobworker.py:process_queue_item`)
   - Downloads each blob from upstream registry
   - Creates ImageStoragePlacement for each downloaded blob
   - **BUG**: Does NOT reset the manifestsecuritystatus or trigger rescan

4. **Manifest Never Gets Rescanned**
   - All blobs are now downloaded and have ImageStoragePlacement
   - Manifest is ready for scanning, but manifestsecuritystatus shows `index_status = MANIFEST_UNSUPPORTED`
   - Security worker's iterator explicitly excludes `MANIFEST_UNSUPPORTED` from reindexing (`secscan_v4_model.py:241`)
   - Manifest never gets scanned by Clair

### Key Code Locations

- **Proxy Cache Model**: `data/registry_model/registry_proxy_model.py`
  - Line 699-727: `_create_placeholder_blobs()` - Creates placeholder blobs and queues downloads
  - Line 641-661: `_download_blob()` - Downloads blob from upstream

- **Proxy Cache Worker**: `workers/proxycacheblobworker.py`
  - Line 28-63: `process_queue_item()` - Downloads blobs but doesn't trigger rescan

- **Security Scanner Model**: `data/secscan_model/secscan_v4_model.py`
  - Line 390-401: Marks manifest as MANIFEST_UNSUPPORTED when no layers found
  - Line 241: Explicitly excludes MANIFEST_UNSUPPORTED from reindexing
  - Line 343-358: `mark_manifest_unsupported()` function

- **Security Worker**: `workers/securityworker/securityworker.py`
  - Line 31-42: `_index_in_scanner()` - Main indexing operation
  - Line 44-59: `_index_recent_manifests_in_scanner()` - Indexes recent manifests

## Test Coverage Assessment

### Existing Coverage

**Proxy Cache Tests** (`workers/test/test_proxycacheblobworker.py`):
- ✅ Tests blob download logic
- ✅ Tests handling of None username for public repositories
- ❌ NO tests for manifestsecuritystatus interaction
- ❌ NO tests for triggering security scans after blob download

**Security Scanning Tests** (`data/secscan_model/test/test_secscan_v4_model.py`):
- ✅ Tests MANIFEST_UNSUPPORTED status handling
- ✅ Tests manifest indexing workflow
- ❌ NO tests for proxy cache + security scanning integration

**Missing Test Coverage**:
1. No integration tests for proxy cache + Clair scanning workflow
2. No tests verifying manifestsecuritystatus reset after blob download
3. No tests for the complete flow: proxy pull → blob download → security scan

## Proposed Solution

### Option A: Delete manifestsecuritystatus After All Blobs Downloaded (Recommended)

**Approach**: When the last blob for a manifest is downloaded, delete the manifestsecuritystatus record. The security worker will then pick it up as "not yet indexed" and scan it normally.

**Advantages**:
- Cleanest solution - lets existing security worker flow handle scanning
- Minimal code changes
- No risk of race conditions with security worker
- Consistent with how new manifests are handled

**Implementation Steps**:
1. Add function to check if all blobs for a manifest have ImageStoragePlacement
2. After successful blob download in ProxyCacheBlobWorker, check if all blobs are complete
3. If complete, delete manifestsecuritystatus record with index_status = MANIFEST_UNSUPPORTED
4. Security worker will pick up manifest in next indexing cycle

### Option B: Reset index_status to Allow Reindexing

**Approach**: When all blobs are downloaded, update the manifestsecuritystatus record to set index_status to FAILED or delete the indexer_hash to force reindexing.

**Advantages**:
- Preserves history of previous scan attempts
- Can track when transition happened

**Disadvantages**:
- More complex logic
- May still be excluded by security worker depending on implementation
- Requires modifying security worker's query logic

### Option C: Queue Immediate Rescan

**Approach**: Create a new queue or mechanism to trigger immediate security scan when all blobs are downloaded.

**Advantages**:
- Fastest time to scan result
- Most explicit approach

**Disadvantages**:
- Most complex implementation
- Requires new queue infrastructure
- May duplicate security worker functionality

## Recommended Implementation Plan

### Phase 1: Core Fix (Option A)

#### 1.1 Add Helper Function to Check Blob Completion

**File**: `workers/proxycacheblobworker.py`

Add function to check if all blobs for a manifest are downloaded:

```python
def _all_blobs_downloaded_for_manifest(self, manifest_id, repo_id):
    """
    Check if all blobs associated with a manifest have ImageStoragePlacement.
    Returns True if all blobs are downloaded, False otherwise.
    """
    from data.database import ManifestBlob, ImageStorage, ImageStoragePlacement

    # Get all blobs for this manifest
    blobs = (
        ImageStorage.select(ImageStorage.id)
        .join(ManifestBlob)
        .where(
            ManifestBlob.manifest_id == manifest_id,
            ManifestBlob.repository_id == repo_id
        )
    )

    # Check if each blob has a placement
    for blob in blobs:
        try:
            ImageStoragePlacement.select().where(
                ImageStoragePlacement.storage == blob
            ).get()
        except ImageStoragePlacement.DoesNotExist:
            return False

    return True
```

#### 1.2 Reset Security Status After Download

**File**: `workers/proxycacheblobworker.py`

Modify `process_queue_item()` to reset security status after blob download:

```python
def process_queue_item(self, job_details):
    repo_id = job_details["repo_id"]
    namespace_name = job_details["namespace"]
    digest = job_details["digest"]
    username = job_details["username"]

    repo_name = repository.lookup_repository(repo_id).name
    repo_ref = RepositoryReference.for_id(repo_id)
    user_ref = user.get_username(username) if username else None

    registry_proxy_model = ProxyModel(
        namespace_name,
        repo_name,
        user_ref,
    )

    logger.debug(
        "Starting proxy cache blob download for digest %s for repo id %s",
        digest,
        repo_id,
    )

    if self._should_download_blob(digest, repo_id, registry_proxy_model):
        try:
            registry_proxy_model._download_blob(
                repo_ref,
                digest,
            )

            # NEW CODE: Check if this blob is part of a manifest
            # and if all blobs for that manifest are now downloaded
            self._reset_security_status_if_complete(digest, repo_id)

        except:
            logger.exception(
                "Exception when downloading blob %s for repo id %s for proxy cache",
                digest,
                repo_id,
            )

    return

def _reset_security_status_if_complete(self, blob_digest, repo_id):
    """
    Check if the downloaded blob completes all blobs for any manifest.
    If so, reset the security status to allow Clair scanning.
    """
    from data.database import (
        ManifestBlob, ManifestSecurityStatus, Manifest,
        IndexStatus, db_transaction
    )

    # Find all manifests that include this blob
    manifests = (
        Manifest.select(Manifest.id)
        .join(ManifestBlob)
        .join(ImageStorage)
        .where(
            ManifestBlob.repository_id == repo_id,
            ImageStorage.content_checksum == blob_digest
        )
        .distinct()
    )

    for manifest in manifests:
        # Check if all blobs for this manifest are downloaded
        if self._all_blobs_downloaded_for_manifest(manifest.id, repo_id):
            # Delete MANIFEST_UNSUPPORTED status to allow rescanning
            with db_transaction():
                deleted = ManifestSecurityStatus.delete().where(
                    ManifestSecurityStatus.manifest == manifest.id,
                    ManifestSecurityStatus.repository == repo_id,
                    ManifestSecurityStatus.index_status == IndexStatus.MANIFEST_UNSUPPORTED
                ).execute()

                if deleted > 0:
                    logger.info(
                        "Reset security status for manifest %s in repo %s - all blobs downloaded",
                        manifest.id,
                        repo_id
                    )
```

#### 1.3 Import Required Modules

**File**: `workers/proxycacheblobworker.py`

Add required imports at the top of the file:

```python
from data.database import (
    ImageStorage, ImageStoragePlacement, ManifestBlob,
    Manifest, ManifestSecurityStatus, IndexStatus, db_transaction
)
```

### Phase 2: Comprehensive Testing

#### 2.1 Unit Tests

**File**: `workers/test/test_proxycacheblobworker.py`

Add tests for the new functionality:

```python
def test_all_blobs_downloaded_for_manifest(proxy_cache_blob_worker, initialized_db):
    """Test detection of all blobs being downloaded for a manifest"""
    # TODO: Implement test that:
    # 1. Creates a manifest with multiple placeholder blobs
    # 2. Downloads some blobs (creates ImageStoragePlacement)
    # 3. Verifies _all_blobs_downloaded_for_manifest returns False
    # 4. Downloads remaining blobs
    # 5. Verifies _all_blobs_downloaded_for_manifest returns True
    pass

def test_reset_security_status_after_blob_download(proxy_cache_blob_worker, initialized_db):
    """Test that security status is reset when all blobs are downloaded"""
    # TODO: Implement test that:
    # 1. Creates a manifest marked as MANIFEST_UNSUPPORTED
    # 2. Downloads all blobs for the manifest
    # 3. Verifies manifestsecuritystatus record is deleted
    pass

def test_partial_blob_download_does_not_reset_status(proxy_cache_blob_worker, initialized_db):
    """Test that security status is NOT reset when only some blobs are downloaded"""
    # TODO: Implement test that:
    # 1. Creates a manifest with multiple blobs
    # 2. Downloads only some blobs
    # 3. Verifies manifestsecuritystatus record still exists
    pass
```

#### 2.2 Integration Tests

**File**: `test/test_proxy_cache_security_integration.py` (new file)

Create comprehensive integration test:

```python
def test_proxy_cache_triggers_security_scan_after_blob_download():
    """
    Integration test for the complete flow:
    1. Pull image through proxy cache
    2. Verify manifest is created with placeholder blobs
    3. Verify manifest is marked as MANIFEST_UNSUPPORTED
    4. Wait for blob downloads to complete
    5. Verify manifestsecuritystatus is reset
    6. Verify security worker picks up manifest for scanning
    7. Verify scan completes successfully
    """
    # TODO: Implement full integration test
    pass
```

#### 2.3 E2E Tests

**File**: `test/registry/test_proxy_cache_e2e.py`

Add E2E test that mirrors the bug reproduction steps:

```python
def test_proxy_cache_partial_then_full_pull_triggers_scan():
    """
    E2E test matching bug reproduction:
    1. Pull part of image layers without proxy
    2. Pull remaining layers using Quay proxy
    3. Wait for Quay to cache missing layers
    4. Verify Clair scan result shows vulnerabilities, not "unsupported"
    """
    # TODO: Implement E2E test
    pass
```

### Phase 3: Additional Improvements (Optional)

#### 3.1 Add Metrics

Track when security status is reset for monitoring:

```python
from util.metrics.prometheus import proxy_cache_security_reset_counter

proxy_cache_security_reset_counter.inc()
```

#### 3.2 Add Configuration Option

Add config option to control behavior:

```yaml
# config.yaml
PROXY_CACHE_AUTO_RESET_SECURITY_STATUS: true
```

#### 3.3 Optimize Query Performance

If performance is a concern with large manifests:
- Add database index on (ManifestBlob.manifest_id, ManifestBlob.repository_id)
- Cache blob count per manifest to avoid repeated queries

## Implementation Checklist

- [ ] Phase 1: Core Fix
  - [ ] Add `_all_blobs_downloaded_for_manifest()` helper function
  - [ ] Add `_reset_security_status_if_complete()` function
  - [ ] Modify `process_queue_item()` to call reset function
  - [ ] Add required imports
  - [ ] Test locally with proxy cache setup

- [ ] Phase 2: Testing
  - [ ] Add unit tests for blob completion detection
  - [ ] Add unit tests for security status reset
  - [ ] Add integration test for full workflow
  - [ ] Add E2E test matching bug reproduction
  - [ ] Verify all tests pass

- [ ] Phase 3: Documentation & Review
  - [ ] Update CLAUDE.md with new behavior
  - [ ] Add inline code documentation
  - [ ] Create PR with detailed description
  - [ ] Request code review from Quay team

## Risks and Mitigation

### Risk 1: Race Condition with Security Worker

**Risk**: Security worker might scan manifest while blobs are being downloaded.

**Mitigation**:
- Security worker already handles this - it marks manifest as UNSUPPORTED if no layers found
- Our fix only resets status AFTER all blobs are downloaded
- Security worker will rescan on next cycle (default 30 seconds)

### Risk 2: Performance Impact

**Risk**: Checking all blobs for every blob download could be expensive for large manifests.

**Mitigation**:
- Check is only performed when a blob is actually downloaded (not already present)
- Query is scoped to single manifest + repo
- Can optimize with caching if needed

### Risk 3: Incomplete Blob Downloads

**Risk**: What if blob download fails partway through?

**Mitigation**:
- Only reset status when ALL blobs have ImageStoragePlacement
- Failed downloads don't create ImageStoragePlacement
- Blob download queue has retry logic built in

### Risk 4: Database Transaction Conflicts

**Risk**: Concurrent updates to manifestsecuritystatus.

**Mitigation**:
- Use db_transaction() for atomic delete
- DELETE operation is idempotent (safe to run multiple times)
- Security worker also uses transactions for status updates

## Success Criteria

1. ✅ After pulling all layers through proxy cache, Clair automatically scans the image
2. ✅ Vulnerability reports appear within 1-2 security worker cycles (30-60 seconds)
3. ✅ No manual database intervention required
4. ✅ Existing proxy cache functionality continues to work
5. ✅ All new tests pass
6. ✅ No performance degradation

## Rollback Plan

If issues arise after deployment:

1. **Immediate Rollback**: Remove the call to `_reset_security_status_if_complete()` from `process_queue_item()`
2. **Temporary Workaround**: Users can continue using manual SQL workaround
3. **Investigation**: Review logs for errors during blob download or status reset

## Future Enhancements

1. **Proactive Scanning**: Queue manifest for immediate scan instead of waiting for security worker cycle
2. **Status Tracking**: Add new index_status value for "pending blob download"
3. **Metrics Dashboard**: Add Grafana dashboard showing proxy cache → security scan pipeline
4. **Configuration**: Make security reset behavior configurable per organization/repo

## References

- **Bug Report**: "After pulling all layers of an image Clair is not triggered to rescan"
- **Related Code**:
  - `data/registry_model/registry_proxy_model.py`: Proxy cache implementation
  - `workers/proxycacheblobworker.py`: Blob download worker
  - `data/secscan_model/secscan_v4_model.py`: Security scanning model
  - `workers/securityworker/securityworker.py`: Security worker
- **Database Schema**:
  - `ManifestSecurityStatus`: Tracks scanning status per manifest
  - `ImageStoragePlacement`: Tracks blob storage locations
  - `ManifestBlob`: Links manifests to blobs
