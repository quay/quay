import {useMemo} from 'react';
import {Tag} from 'src/resources/TagResource';

// D3 category10-like colors matching the Angular implementation
const TRACK_COLORS = [
  '#1f77b4', // blue
  '#ff7f0e', // orange
  '#2ca02c', // green
  '#d62728', // red
  '#9467bd', // purple
  '#8c564b', // brown
  '#e377c2', // pink
  '#7f7f7f', // gray
  '#bcbd22', // olive
  '#17becf', // cyan
];

function getTrackColor(index: number): string {
  return TRACK_COLORS[index % TRACK_COLORS.length];
}

export interface TrackEntry {
  manifest_digest: string;
  color: string;
  count: number;
  tags: Tag[];
  index_range: {start: number; end: number};
  tagIndices: Set<number>;
}

export interface ManifestTrack {
  entries: TrackEntry[];
  entryByIndex: Record<number, TrackEntry>;
}

export interface ComputedTracks {
  tracks: ManifestTrack[];
  trackCount: number;
}

export interface UseManifestTracksResult extends ComputedTracks {
  getTrackEntry: (trackIndex: number, rowIndex: number) => TrackEntry | null;
  getLineClass: (
    trackIndex: number,
    rowIndex: number,
  ) => 'start' | 'middle' | 'end' | '';
}

const MAX_TRACK_COUNT = 5;

/**
 * Pure function that computes manifest tracks from a list of tags.
 * Exported for testing without React hooks.
 */
export function computeManifestTracks(tags: Tag[]): ComputedTracks {
  if (!tags || tags.length === 0) {
    return {tracks: [], trackCount: 0};
  }

  // Step 1: Group tags by manifest_digest and record their row indices
  const manifestMap: Record<string, Tag[]> = {};
  const manifestIndexMap: Record<
    string,
    {start: number; end: number; indices: Set<number>}
  > = {};
  const manifestDigests: string[] = [];

  for (let i = 0; i < tags.length; i++) {
    const tag = tags[i];
    if (!tag.manifest_digest) {
      continue;
    }

    if (!manifestMap[tag.manifest_digest]) {
      manifestMap[tag.manifest_digest] = [];
      manifestDigests.push(tag.manifest_digest);
      manifestIndexMap[tag.manifest_digest] = {
        start: i,
        end: i,
        indices: new Set<number>(),
      };
    }

    manifestMap[tag.manifest_digest].push(tag);
    manifestIndexMap[tag.manifest_digest].end = i;
    manifestIndexMap[tag.manifest_digest].indices.add(i);
  }

  // Step 2: Build track entries for manifests shared by 2+ tags
  const manifestTracks: ManifestTrack[] = [];
  let colorIndex = 0;

  // Sort digests for consistent color assignment
  manifestDigests.sort();

  for (const digest of manifestDigests) {
    const tagsForDigest = manifestMap[digest];
    if (tagsForDigest.length < 2) {
      continue;
    }

    const indexData = manifestIndexMap[digest];
    const trackEntry: TrackEntry = {
      manifest_digest: digest,
      color: getTrackColor(colorIndex),
      count: tagsForDigest.length,
      tags: tagsForDigest,
      index_range: {start: indexData.start, end: indexData.end},
      tagIndices: indexData.indices,
    };
    colorIndex++;

    // Step 3: Find a track where this entry doesn't overlap existing entries
    let targetTrack: ManifestTrack | null = null;

    for (const track of manifestTracks) {
      let canAdd = true;
      for (const existing of track.entries) {
        const overlaps =
          Math.max(existing.index_range.start, trackEntry.index_range.start) <=
          Math.min(existing.index_range.end, trackEntry.index_range.end);
        if (overlaps) {
          canAdd = false;
          break;
        }
      }
      if (canAdd) {
        targetTrack = track;
        break;
      }
    }

    // Step 4: Add to existing track or create new one
    if (targetTrack) {
      targetTrack.entries.push(trackEntry);
      for (
        let j = trackEntry.index_range.start;
        j <= trackEntry.index_range.end;
        j++
      ) {
        targetTrack.entryByIndex[j] = trackEntry;
      }
    } else {
      const entryByIndex: Record<number, TrackEntry> = {};
      for (
        let j = trackEntry.index_range.start;
        j <= trackEntry.index_range.end;
        j++
      ) {
        entryByIndex[j] = trackEntry;
      }
      manifestTracks.push({
        entries: [trackEntry],
        entryByIndex,
      });
    }
  }

  const limited = manifestTracks.slice(0, MAX_TRACK_COUNT);
  return {tracks: limited, trackCount: limited.length};
}

/** Get the track entry at a given track index and row index. */
export function getTrackEntryAt(
  tracks: ManifestTrack[],
  trackIndex: number,
  rowIndex: number,
): TrackEntry | null {
  if (trackIndex < 0 || trackIndex >= tracks.length) {
    return null;
  }
  return tracks[trackIndex].entryByIndex[rowIndex] || null;
}

/** Get the line class (start/middle/end) for a given position. */
export function getLineClassAt(
  tracks: ManifestTrack[],
  trackIndex: number,
  rowIndex: number,
): 'start' | 'middle' | 'end' | '' {
  const entry = getTrackEntryAt(tracks, trackIndex, rowIndex);
  if (!entry) {
    return '';
  }
  if (rowIndex === entry.index_range.start) {
    return 'start';
  }
  if (rowIndex === entry.index_range.end) {
    return 'end';
  }
  if (rowIndex > entry.index_range.start && rowIndex < entry.index_range.end) {
    return 'middle';
  }
  return '';
}

/**
 * Hook to calculate manifest tracks for visualizing tags that share the same
 * manifest digest. Tags sharing a manifest are connected by vertical lines
 * with colored dots in the tags table.
 *
 * Uses a track-packing algorithm: each "track" is a vertical lane. Multiple
 * manifest groups can share a lane if their row ranges don't overlap.
 */
export function useManifestTracks(tags: Tag[]): UseManifestTracksResult {
  const {tracks, trackCount} = useMemo(
    () => computeManifestTracks(tags),
    [tags],
  );

  const getTrackEntry = (
    trackIndex: number,
    rowIndex: number,
  ): TrackEntry | null => getTrackEntryAt(tracks, trackIndex, rowIndex);

  const getLineClass = (
    trackIndex: number,
    rowIndex: number,
  ): 'start' | 'middle' | 'end' | '' =>
    getLineClassAt(tracks, trackIndex, rowIndex);

  return {tracks, trackCount, getTrackEntry, getLineClass};
}
