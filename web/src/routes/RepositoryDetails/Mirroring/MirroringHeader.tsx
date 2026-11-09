import React from 'react';
import {Content, Title} from '@patternfly/react-core';
import {Link, useLocation} from 'react-router-dom';
import {getRepoDetailPath} from 'src/routes/NavigationPath';

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
  const location = useLocation();
  return (
    <>
      <Content>
        <Title headingLevel="h2">Repository Mirroring</Title>
      </Content>

      <Content>
        {isConfigured ? (
          <Content component="p">
            This repository is configured as a mirror. While enabled, Quay will
            periodically replicate any matching images on the external registry.
            Users cannot manually push to this repository.
          </Content>
        ) : (
          <Content component="p">
            This feature will convert{' '}
            <Link
              to={`${getRepoDetailPath(
                location.pathname,
                namespace,
                repoName,
              )}?tab=information`}
            >
              <strong>
                {namespace}/{repoName}
              </strong>
            </Link>{' '}
            into a mirror. Changes to the external repository will be duplicated
            here. While enabled, users will be unable to push images to this
            repository.
          </Content>
        )}
      </Content>
    </>
  );
};
