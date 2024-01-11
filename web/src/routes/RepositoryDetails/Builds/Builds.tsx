import {Card, PageSection} from '@patternfly/react-core';
import BuildHistory from './BuildHistory';
import BuildTriggers from './BuildTriggers';
import {RepositoryDetails} from 'src/resources/RepositoryResource';

export default function Builds(props: BuildsProps) {
  return (
    <PageSection>
      <Card>
        <BuildHistory org={props.org} repo={props.repo} />
      </Card>
      <br />
      <Card>
        <BuildTriggers
          org={props.org}
          repo={props.repo}
          setupTriggerUuid={props.setupTriggerUuid}
          repoDetails={props.repoDetails}
        />
      </Card>
    </PageSection>
  );
}

interface BuildsProps {
  org: string;
  repo: string;
  setupTriggerUuid?: string;
  repoDetails: RepositoryDetails;
}
