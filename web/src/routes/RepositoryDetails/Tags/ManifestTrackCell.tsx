import {Tooltip} from '@patternfly/react-core';
import React from 'react';
import {TrackEntry} from './useManifestTracks';
import './Tags.css';

interface ManifestTrackCellProps {
  trackCount: number;
  rowIndex: number;
  getTrackEntry: (trackIndex: number, rowIndex: number) => TrackEntry | null;
  getLineClass: (
    trackIndex: number,
    rowIndex: number,
  ) => 'start' | 'middle' | 'end' | '';
  onDotClick?: (manifestDigest: string) => void;
  /** 'tag' for main rows, 'continuation' for SubRow and expanded rows */
  mode: 'tag' | 'continuation';
}

const LANE_WIDTH = 24;

/**
 * Renders all manifest track lanes within a single table cell.
 * Each lane shows a dot (on rows with matching tags) and a vertical
 * connecting line between the first and last occurrence of a manifest.
 */
const ManifestTrackCell: React.FC<ManifestTrackCellProps> = ({
  trackCount,
  rowIndex,
  getTrackEntry,
  getLineClass,
  onDotClick,
  mode,
}) => {
  if (trackCount === 0) {
    return null;
  }

  return (
    <div
      className="manifest-track-container"
      style={{width: trackCount * LANE_WIDTH}}
    >
      {Array.from({length: trackCount}).map((_, trackIdx) => {
        const entry = getTrackEntry(trackIdx, rowIndex);
        const lineClass = getLineClass(trackIdx, rowIndex);

        if (mode === 'continuation') {
          // SubRow / expanded rows: only show continuing middle lines
          const showLine = lineClass === 'start' || lineClass === 'middle';
          return (
            <div
              key={trackIdx}
              className="manifest-track-lane"
              style={{left: trackIdx * LANE_WIDTH}}
            >
              {showLine && entry && (
                <div
                  className="manifest-track-line middle"
                  style={{borderColor: entry.color}}
                />
              )}
            </div>
          );
        }

        // Tag rows: show dots and lines
        if (!entry || !lineClass) {
          return (
            <div
              key={trackIdx}
              className="manifest-track-lane"
              style={{left: trackIdx * LANE_WIDTH}}
            />
          );
        }

        const hasTagAtRow = entry.tagIndices.has(rowIndex);

        return (
          <div
            key={trackIdx}
            className="manifest-track-lane"
            style={{left: trackIdx * LANE_WIDTH}}
          >
            {hasTagAtRow && (
              <Tooltip
                content={
                  <div>
                    <div style={{marginBottom: '4px'}}>
                      <strong>{entry.count} tags</strong> share this manifest
                    </div>
                    <div style={{fontSize: '12px', fontFamily: 'monospace'}}>
                      {entry.manifest_digest.substring(0, 19)}
                    </div>
                  </div>
                }
              >
                <div
                  className="manifest-track-dot"
                  style={{borderColor: entry.color}}
                  onClick={() => onDotClick?.(entry.manifest_digest)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      onDotClick?.(entry.manifest_digest);
                    }
                  }}
                  aria-label={`Select all ${
                    entry.count
                  } tags with manifest ${entry.manifest_digest.substring(
                    0,
                    12,
                  )}`}
                />
              </Tooltip>
            )}
            <div
              className={`manifest-track-line ${lineClass}`}
              style={{borderColor: entry.color}}
            />
          </div>
        );
      })}
    </div>
  );
};

export default ManifestTrackCell;
