import {useMemo} from 'react';
import {Tag} from 'src/resources/TagResource';
import {getTrackColor} from 'src/libs/utils';

export interface TrackEntry {
  manifest_digest: string;
  color: string;
  count: number;
  tags: Tag[];
  index_range: {start: number; end: number};
  tagIndices: Set<number>; // Row indices that actually have this manifest
}

export interface ManifestTrack {
  entries: TrackEntry[];
  entryByIndex: Record<number, TrackEntry>;
}

export interface UseManifestTracksResult {
  tracks: ManifestTrack[];
  getTrackEntry: (trackIndex: number, rowIndex: number) => TrackEntry | null;
  getLineClass: (
    trackIndex: number,
    rowIndex: number,
  ) => 'start' | 'middle' | 'end' | '';
  trackCount: number;
}

const MAX_TRACK_COUNT = 5;

/**
 * Hook to calculate manifest tracks for visualizing tags that share the same manifest digest.
 * Tags sharing a manifest are connected by vertical lines with colored dots.
 *
 * @param tags - Array of tags to analyze
 * @returns Track data and helper functions for rendering
 */
export function useManifestTracks(tags: Tag[]): UseManifestTracksResult {
  const {tracks, trackCount} = useMemo(() => {
    if (!tags || tags.length === 0) {
      return {tracks: [], trackCount: 0};
    }

    // Step 1: Group tags by manifest_digest and track their indices
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

    // Step 2: Create track entries for manifests with 2+ tags
    const manifestTracks: ManifestTrack[] = [];
    let colorIndex = 0;

    // Sort digests to ensure consistent color assignment
    manifestDigests.sort();

    for (const manifest_digest of manifestDigests) {
      const tagsForManifest = manifestMap[manifest_digest];

      // Only create tracks for manifests with 2+ tags
      if (tagsForManifest.length < 2) {
        continue;
      }

      const indexData = manifestIndexMap[manifest_digest];
      const trackEntry: TrackEntry = {
        manifest_digest,
        color: getTrackColor(colorIndex),
        count: tagsForManifest.length,
        tags: tagsForManifest,
        index_range: {start: indexData.start, end: indexData.end},
        tagIndices: indexData.indices,
      };

      colorIndex++;

      // Step 3: Find a track where this entry doesn't overlap with existing entries
      let existingTrack: ManifestTrack | null = null;

      for (const track of manifestTracks) {
        let canAddToTrack = true;

        for (const entry of track.entries) {
          // Check if ranges overlap
          const overlaps =
            Math.max(entry.index_range.start, trackEntry.index_range.start) <=
            Math.min(entry.index_range.end, trackEntry.index_range.end);

          if (overlaps) {
            canAddToTrack = false;
            break;
          }
        }

        if (canAddToTrack) {
          existingTrack = track;
          break;
        }
      }

      // Step 4: Add entry to existing track or create new track
      if (existingTrack) {
        existingTrack.entries.push(trackEntry);
        for (
          let j = trackEntry.index_range.start;
          j <= trackEntry.index_range.end;
          j++
        ) {
          existingTrack.entryByIndex[j] = trackEntry;
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

    // Limit to MAX_TRACK_COUNT tracks
    const limitedTracks = manifestTracks.slice(0, MAX_TRACK_COUNT);

    return {
      tracks: limitedTracks,
      trackCount: limitedTracks.length,
    };
  }, [tags]);

  const getTrackEntry = (
    trackIndex: number,
    rowIndex: number,
  ): TrackEntry | null => {
    if (trackIndex < 0 || trackIndex >= tracks.length) {
      return null;
    }
    return tracks[trackIndex].entryByIndex[rowIndex] || null;
  };

  const getLineClass = (
    trackIndex: number,
    rowIndex: number,
  ): 'start' | 'middle' | 'end' | '' => {
    const entry = getTrackEntry(trackIndex, rowIndex);
    if (!entry) {
      return '';
    }

    if (rowIndex === entry.index_range.start) {
      return 'start';
    }
    if (rowIndex === entry.index_range.end) {
      return 'end';
    }
    if (
      rowIndex > entry.index_range.start &&
      rowIndex < entry.index_range.end
    ) {
      return 'middle';
    }

    return '';
  };

  return {
    tracks,
    getTrackEntry,
    getLineClass,
    trackCount,
  };
}
