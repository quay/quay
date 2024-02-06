import {Card, PageSection} from '@patternfly/react-core';
import BuildHistory from './BuildHistory';
import BuildTriggers from './BuildTriggers';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {useBuildTriggers} from 'src/hooks/UseBuildTriggers';
import {LoadingPage} from 'src/components/LoadingPage';
import RequestError from 'src/components/errors/RequestError';

export default function Builds(props: BuildsProps) {
  const {triggers, isLoading, isError, error} = useBuildTriggers(
    props.org,
    props.repo,
  );

  if (isLoading) {
    return <LoadingPage />;
  }

  if (isError) {
    return <RequestError message={error.toString()} />;
  }

  return (
    <PageSection>
      <Card>
        <BuildHistory
          org={props.org}
          repo={props.repo}
          repoDetails={props.repoDetails}
          triggers={triggers}
        />
      </Card>
      <br />
      <Card>
        <BuildTriggers
          org={props.org}
          repo={props.repo}
          triggers={triggers}
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
