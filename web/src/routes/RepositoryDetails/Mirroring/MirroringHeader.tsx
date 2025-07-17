import React from 'react';
import {TextContent, Text, Title} from '@patternfly/react-core';

interface MirroringHeaderProps {
  namespace: string;
  repoName: string;
  isConfigured: boolean;
}

export const MirroringHeader: React.FC<MirroringHeaderProps> = ({
  namespace,
  repoName,
  isConfigured,
}) => {
  return (
    <>
      <TextContent>
        <Title headingLevel="h2">Repository Mirroring</Title>
      </TextContent>

      <TextContent>
        {isConfigured ? (
          <Text>
            This repository is configured as a mirror. While enabled, Quay will
            periodically replicate any matching images on the external registry.
            Users cannot manually push to this repository.
          </Text>
        ) : (
          <Text>
            This feature will convert{' '}
            <strong>
              {namespace}/{repoName}
            </strong>{' '}
            into a mirror. Changes to the external repository will be duplicated
            here. While enabled, users will be unable to push images to this
            repository.
          </Text>
        )}
      </TextContent>
    </>
  );
};
