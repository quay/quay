import {
  computeManifestTracks,
  getTrackEntryAt,
  getLineClassAt,
} from '../useManifestTracks';
import {Tag} from 'src/resources/TagResource';

function makeTag(name: string, manifest_digest: string): Tag {
  return {
    name,
    manifest_digest,
    is_manifest_list: false,
    last_modified: '2025-01-01T00:00:00Z',
    reversion: false,
    size: 1024,
    start_ts: 0,
    manifest_list: null as any,
  };
}

describe('computeManifestTracks', () => {
  it('returns empty tracks for empty tags array', () => {
    const result = computeManifestTracks([]);
    expect(result.tracks).toEqual([]);
    expect(result.trackCount).toBe(0);
  });

  it('returns empty tracks for null/undefined input', () => {
    const result = computeManifestTracks(null as any);
    expect(result.tracks).toEqual([]);
    expect(result.trackCount).toBe(0);
  });

  it('returns no tracks when all tags have unique digests', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:bbb'),
      makeTag('v3', 'sha256:ccc'),
    ];
    const result = computeManifestTracks(tags);
    expect(result.trackCount).toBe(0);
  });

  it('returns no tracks for a single tag', () => {
    const tags = [makeTag('v1', 'sha256:aaa')];
    const result = computeManifestTracks(tags);
    expect(result.trackCount).toBe(0);
  });

  it('creates one track for two tags sharing the same digest', () => {
    const tags = [makeTag('v1', 'sha256:aaa'), makeTag('v2', 'sha256:aaa')];
    const result = computeManifestTracks(tags);
    expect(result.trackCount).toBe(1);

    const entry = getTrackEntryAt(result.tracks, 0, 0);
    expect(entry).not.toBeNull();
    expect(entry!.manifest_digest).toBe('sha256:aaa');
    expect(entry!.count).toBe(2);
    expect(entry!.index_range).toEqual({start: 0, end: 1});
  });

  it('packs non-overlapping groups into the same track', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:aaa'),
      makeTag('v3', 'sha256:bbb'),
      makeTag('v4', 'sha256:bbb'),
    ];
    const result = computeManifestTracks(tags);
    // aaa: [0,1], bbb: [2,3] - no overlap, single track
    expect(result.trackCount).toBe(1);
    expect(result.tracks[0].entries.length).toBe(2);
  });

  it('creates separate tracks for overlapping ranges', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:bbb'),
      makeTag('v3', 'sha256:aaa'),
      makeTag('v4', 'sha256:bbb'),
    ];
    const result = computeManifestTracks(tags);
    // aaa: [0,2], bbb: [1,3] - overlapping, need 2 tracks
    expect(result.trackCount).toBe(2);
  });

  it('caps tracks at 5', () => {
    // Create 6 overlapping pairs to force 6 tracks
    const tags = [
      makeTag('a1', 'sha256:aaa'),
      makeTag('b1', 'sha256:bbb'),
      makeTag('c1', 'sha256:ccc'),
      makeTag('d1', 'sha256:ddd'),
      makeTag('e1', 'sha256:eee'),
      makeTag('f1', 'sha256:fff'),
      makeTag('a2', 'sha256:aaa'),
      makeTag('b2', 'sha256:bbb'),
      makeTag('c2', 'sha256:ccc'),
      makeTag('d2', 'sha256:ddd'),
      makeTag('e2', 'sha256:eee'),
      makeTag('f2', 'sha256:fff'),
    ];
    const result = computeManifestTracks(tags);
    expect(result.trackCount).toBeLessThanOrEqual(5);
  });

  it('assigns distinct colors to different track entries', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:bbb'),
      makeTag('v3', 'sha256:aaa'),
      makeTag('v4', 'sha256:bbb'),
    ];
    const result = computeManifestTracks(tags);
    const entry0 = getTrackEntryAt(result.tracks, 0, 0);
    const entry1 = getTrackEntryAt(result.tracks, 1, 1);
    expect(entry0).not.toBeNull();
    expect(entry1).not.toBeNull();
    expect(entry0!.color).not.toBe(entry1!.color);
  });

  it('tracks tagIndices correctly for non-adjacent tags', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:bbb'),
      makeTag('v3', 'sha256:aaa'),
    ];
    const result = computeManifestTracks(tags);
    const entry = getTrackEntryAt(result.tracks, 0, 0);
    expect(entry).not.toBeNull();
    expect(entry!.tagIndices.has(0)).toBe(true);
    expect(entry!.tagIndices.has(1)).toBe(false);
    expect(entry!.tagIndices.has(2)).toBe(true);
  });

  it('skips tags without manifest_digest', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      {...makeTag('v2', ''), manifest_digest: ''},
      makeTag('v3', 'sha256:aaa'),
    ];
    const result = computeManifestTracks(tags);
    expect(result.trackCount).toBe(1);
    const entry = getTrackEntryAt(result.tracks, 0, 0);
    expect(entry!.count).toBe(2);
  });

  it('packs distant non-overlapping entries into the same track', () => {
    // aaa at [0,1], bbb at [3,4]
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:aaa'),
      makeTag('v3', 'sha256:ccc'),
      makeTag('v4', 'sha256:bbb'),
      makeTag('v5', 'sha256:bbb'),
    ];
    const result = computeManifestTracks(tags);
    expect(result.trackCount).toBe(1);
    expect(result.tracks[0].entries.length).toBe(2);
  });
});

describe('getTrackEntryAt', () => {
  it('returns null for invalid track index', () => {
    const tags = [makeTag('v1', 'sha256:aaa'), makeTag('v2', 'sha256:aaa')];
    const {tracks} = computeManifestTracks(tags);
    expect(getTrackEntryAt(tracks, -1, 0)).toBeNull();
    expect(getTrackEntryAt(tracks, 5, 0)).toBeNull();
  });

  it('returns null for row outside any entry range', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:aaa'),
      makeTag('v3', 'sha256:bbb'),
    ];
    const {tracks} = computeManifestTracks(tags);
    expect(getTrackEntryAt(tracks, 0, 2)).toBeNull();
  });
});

describe('getLineClassAt', () => {
  it('returns correct class for start, middle, end', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:bbb'),
      makeTag('v3', 'sha256:aaa'),
    ];
    const {tracks} = computeManifestTracks(tags);

    expect(getLineClassAt(tracks, 0, 0)).toBe('start');
    expect(getLineClassAt(tracks, 0, 1)).toBe('middle');
    expect(getLineClassAt(tracks, 0, 2)).toBe('end');
  });

  it('returns empty string for rows outside track range', () => {
    const tags = [
      makeTag('v1', 'sha256:aaa'),
      makeTag('v2', 'sha256:aaa'),
      makeTag('v3', 'sha256:bbb'),
    ];
    const {tracks} = computeManifestTracks(tags);
    expect(getLineClassAt(tracks, 0, 2)).toBe('');
  });

  it('returns empty string for invalid track index', () => {
    const tags = [makeTag('v1', 'sha256:aaa'), makeTag('v2', 'sha256:aaa')];
    const {tracks} = computeManifestTracks(tags);
    expect(getLineClassAt(tracks, -1, 0)).toBe('');
    expect(getLineClassAt(tracks, 99, 0)).toBe('');
  });
});
