import React, {useMemo} from 'react';
import {
  PageSection,
  Title,
  Text,
  TextContent,
  Alert,
} from '@patternfly/react-core';
import {ManifestByDigestResponse, Layer} from 'src/resources/TagResource';
import {LayerItem} from './LayerItem';
import './Layers.scss';

interface LayersProps {
  org: string;
  repo: string;
  digest: string;
  manifestData: ManifestByDigestResponse;
  err?: string;
}

export function Layers(props: LayersProps) {
  // Memoize layer reversal for performance
  const layers = useMemo(() => {
    if (!props.manifestData?.layers) {
      return [];
    }
    return props.manifestData.layers.slice().reverse();
  }, [props.manifestData]);

  // Show error state if manifest fetch failed
  if (props.err && !props.manifestData) {
    return (
      <PageSection>
        <Title headingLevel="h3" className="pf-v5-u-text-align-left">
          Manifest Layers
        </Title>
        <Alert variant="danger" title="Failed to load layers" isInline>
          Unable to retrieve manifest data. Please try again later.
        </Alert>
      </PageSection>
    );
  }

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
      <div
        className="layers-container"
        role="list"
        aria-label="Container image layers"
      >
        {layers.map((layer, index) => (
          <LayerItem
            key={`${layer.blob_digest || 'empty-layer'}-${index}`}
            layer={layer}
            isFirst={index === 0}
            isLast={index === layers.length - 1}
            totalLayers={layers.length}
            layerNumber={layers.length - index}
          />
        ))}
      </div>
    </PageSection>
  );
}
