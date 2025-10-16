import React from 'react';
import {Layer} from 'src/resources/TagResource';
import {LayerCommand} from './LayerCommand';

interface LayerItemProps {
  layer: Layer;
  isFirst: boolean;
  isLast: boolean;
  totalLayers: number;
  layerNumber: number;
}

export function LayerItem(props: LayerItemProps) {
  const {layer} = props;

  // Determine CSS class for styling
  const getClass = (): string => {
    if (layer.index === 0) {
      return 'last';
    }
    if (layer.index === props.totalLayers - 1) {
      return 'first';
    }
    return '';
  };

  const renderLayerContent = () => {
    // Priority: command > comment > blob_digest
    if (layer.command && layer.command.length > 0) {
      return <LayerCommand command={layer.command} />;
    }

    if (layer.comment) {
      return <i>{layer.comment}</i>;
    }

    return <code>{layer.blob_digest}</code>;
  };

  return (
    <div
      className={`manifest-view-layer-element ${getClass()}`}
      role="listitem"
      aria-label={`Layer ${props.layerNumber} of ${props.totalLayers}`}
    >
      <div className="image-command">{renderLayerContent()}</div>
      <div className="image-layer-dot" aria-hidden="true"></div>
      <div className="image-layer-line" aria-hidden="true"></div>
    </div>
  );
}
