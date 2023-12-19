import {Card, PageSection} from '@patternfly/react-core';
import BuildHistory from './BuildHistory';
import BuildTriggers from './BuildTriggers';

export default function Builds(props: BuildsProps) {
  return (
    <PageSection>
      <Card>
        <BuildHistory org={props.org} repo={props.repo} />
      </Card>
      <br />
      <Card>
        <BuildTriggers org={props.org} repo={props.repo} />
      </Card>
    </PageSection>
  );
}

interface BuildsProps {
  org: string;
  repo: string;
}
