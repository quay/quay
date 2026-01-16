import {Tooltip} from '@patternfly/react-core';
import React from 'react';
import {TrackEntry} from './useManifestTracks';
import './Tags.css';

interface ManifestTrackProps {
  trackEntry: TrackEntry | null;
  lineClass: 'start' | 'middle' | 'end' | '';
  rowIndex: number;
  onClick?: () => void;
}

/**
 * Component for rendering a manifest track cell with dot and vertical line.
 * Used to visually connect tags that share the same manifest digest.
 */
const ManifestTrack: React.FC<ManifestTrackProps> = ({
  trackEntry,
  lineClass,
  rowIndex,
  onClick,
}) => {
  if (!trackEntry || !lineClass) {
    return <div className="image-track" />;
  }

  // Check if this row actually has a tag with this manifest
  const hasTagAtRow = trackEntry.tagIndices.has(rowIndex);

  const tooltipContent = (
    <div>
      <div style={{marginBottom: '4px'}}>
        <strong>{trackEntry.count} tags</strong> share this manifest
      </div>
      <div style={{fontSize: '12px', fontFamily: 'monospace'}}>
        {trackEntry.manifest_digest.substring(0, 19)}
      </div>
    </div>
  );

  return (
    <div className="image-track">
      {hasTagAtRow && (
        <Tooltip content={tooltipContent}>
          <div
            className="image-track-dot"
            style={{borderColor: trackEntry.color}}
            onClick={onClick}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                onClick?.();
              }
            }}
            aria-label={`Select all ${trackEntry.count} tags with manifest ${trackEntry.manifest_digest.substring(0, 12)}`}
          />
        </Tooltip>
      )}
      <div
        className={`image-track-line ${lineClass}`}
        style={{borderColor: trackEntry.color}}
      />
    </div>
  );
};

export default ManifestTrack;
