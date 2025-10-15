# Pull Statistics UI Changes

This document describes the UI changes made to display pull statistics in the Tags page.

## Overview

Two new columns have been added to the Tags page table:
- **Last Pulled**: Shows when the tag was last pulled (or "Never" if not pulled)
- **Pull Count**: Shows the number of times the tag has been pulled

## Files Modified

### 1. Frontend TypeScript/React Files

#### `web/src/resources/TagResource.ts`
- **Added fields to Tag interface:**
  ```typescript
  pull_count?: number;
  last_pulled?: string;
  ```
- **Added new interface for pull statistics:**
  ```typescript
  export interface TagPullStatistics {
    tag_name: string;
    tag_pull_count: number;
    last_tag_pull_date: string | null;
    current_manifest_digest: string;
    manifest_pull_count: number;
    last_manifest_pull_date: string | null;
  }
  ```
- **Added API function:**
  ```typescript
  export async function getTagPullStatistics(org: string, repo: string, tag: string)
  ```

#### `web/src/routes/RepositoryDetails/Tags/ColumnNames.ts`
- Added two new column names:
  ```typescript
  lastPulled: 'Last Pulled',
  pullCount: 'Pull Count',
  ```

#### `web/src/routes/RepositoryDetails/Tags/TagsTable.tsx`
- **Added two new table header columns (Th):**
  - Column 7: "Last Pulled" (sortable)
  - Column 8: "Pull Count" (sortable)

- **Added two new table data columns (Td):**
  ```typescript
  <Td dataLabel={ColumnNames.lastPulled}>
    {tag.last_pulled ? formatDate(tag.last_pulled) : 'Never'}
  </Td>
  <Td dataLabel={ColumnNames.pullCount}>
    {tag.pull_count !== undefined ? tag.pull_count : 0}
  </Td>
  ```

#### `web/src/routes/RepositoryDetails/Tags/TagsList.tsx`
- **Updated sorting configuration:**
  ```typescript
  columns: {
    2: (item: Tag) => item.name,           // Tag Name
    4: (item: Tag) => item.size || 0,      // Size
    5: (item: Tag) => item.last_modified,  // Last Modified
    6: (item: Tag) => item.expiration || '', // Expires
    7: (item: Tag) => item.last_pulled || '', // Last Pulled (NEW)
    8: (item: Tag) => item.pull_count || 0,  // Pull Count (NEW)
    9: (item: Tag) => item.manifest_digest,  // Manifest
  }
  ```

- **Added pull statistics fetching in loadTags:**
  ```typescript
  const getPullStats = async (tag: Tag) => {
    const pullStats = await getTagPullStatistics(
      props.organization,
      props.repository,
      tag.name,
    );
    if (pullStats) {
      tag.pull_count = pullStats.tag_pull_count;
      tag.last_pulled = pullStats.last_tag_pull_date;
    }
  };

  // Fetch pull statistics for all tags
  await Promise.all(
    resp.tags.map((tag: Tag) => getPullStats(tag)),
  );
  ```

## Table Column Order

The new Tags table has the following columns in order:

1. Expand (for manifest lists)
2. Select (checkbox)
3. **Tag** (sortable)
4. **Security**
5. **Size** (sortable)
6. **Last Modified** (sortable)
7. **Expires** (sortable)
8. **Last Pulled** (sortable) ← NEW
9. **Pull Count** (sortable) ← NEW
10. **Manifest** (sortable)
11. **Pull** (download icon)
12. Actions (kebab menu)

## Data Flow

1. When the Tags page loads, `loadTags()` is called
2. For each tag, `getTags()` fetches basic tag information
3. For each tag, `getTagPullStatistics()` fetches pull metrics from the API
4. Pull statistics are merged into the tag object:
   - `tag.pull_count` = number of pulls
   - `tag.last_pulled` = ISO timestamp of last pull
5. The table displays the data with formatting:
   - Last Pulled: Formatted date or "Never"
   - Pull Count: Number or 0 if no data

## API Integration

The UI calls the new API endpoint:
```
GET /api/v1/repository/{org}/{repo}/tag/{tag}/pull_statistics
```

Response format:
```json
{
  "tag_name": "latest",
  "tag_pull_count": 25,
  "last_tag_pull_date": "2024-01-01T10:00:00Z",
  "current_manifest_digest": "sha256:abc123...",
  "manifest_pull_count": 45,
  "last_manifest_pull_date": "2024-01-01T10:30:00Z"
}
```

## Feature Flag Support

- If the `FEATURE_IMAGE_PULL_STATS` flag is disabled, the API will return 404
- The `getTagPullStatistics` function catches errors and returns null
- If pull stats are null/unavailable:
  - `pull_count` defaults to 0
  - `last_pulled` displays as "Never"

## Performance Considerations

- Pull statistics are fetched in parallel using `Promise.all()`
- Each tag makes a separate API call to get its statistics
- This happens on initial load and when tags are refreshed
- Consider implementing batch API endpoint for better performance with many tags

## Backward Compatibility

- The new fields are optional (`pull_count?`, `last_pulled?`)
- If the API doesn't return data, the UI gracefully defaults to 0/"Never"
- Works with both old and new Quay versions
