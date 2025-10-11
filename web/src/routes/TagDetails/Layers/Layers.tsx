import React, {useState, useEffect} from 'react';
import {PageSection, Title, Text, TextContent} from '@patternfly/react-core';
import {ManifestByDigestResponse, Layer} from 'src/resources/TagResource';
import {LayerItem} from './LayerItem';
import './Layers.scss';

interface LayersProps {
  org: string;
  repo: string;
  digest: string;
  manifestData: ManifestByDigestResponse;
}

export function Layers(props: LayersProps) {
  const [layers, setLayers] = useState<Layer[]>([]);

  useEffect(() => {
    // Use the manifest data passed from parent instead of making API call
    if (props.manifestData?.layers) {
      // Reverse the layers array
      const reversedLayers = props.manifestData.layers.slice().reverse();
      setLayers(reversedLayers);
    }
  }, [props.manifestData]);

  // Show loading state while waiting for manifest data
  if (!props.manifestData) {
    return (
      <PageSection>
        <TextContent>
          <Text>Loading layers...</Text>
        </TextContent>
      </PageSection>
    );
  }

  if (!layers || layers.length === 0) {
    return (
      <PageSection>
        <Title headingLevel="h3" className="pf-v5-u-text-align-left">
          Manifest Layers
        </Title>
        <TextContent>
          <Text>No layers found for this manifest.</Text>
        </TextContent>
      </PageSection>
    );
  }

  return (
    <PageSection>
      <Title headingLevel="h3" className="pf-v5-u-text-align-left">
        Manifest Layers
      </Title>
      <div className="layers-container">
        {layers.map((layer, index) => (
          <LayerItem
            key={`${layer.blob_digest || layer.index}-${index}`}
            layer={layer}
            isFirst={index === 0}
            isLast={index === layers.length - 1}
            totalLayers={layers.length}
          />
        ))}
      </div>
    </PageSection>
  );
}
