import {GithubIcon, GitlabIcon} from '@patternfly/react-icons';
import LinkOrPlainText from 'src/components/LinkOrPlainText';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {RepositoryBuild} from 'src/resources/BuildResource';

export default function BuildTriggerDescription({
  trigger,
}: {
  trigger: RepositoryBuild['trigger'];
}) {
  const config = useQuayConfig();
  switch (trigger.service) {
    case 'github':
      return (
        <>
          <GithubIcon /> push to GitHub{' '}
          <Conditional
            if={
              !config?.oauth?.GITHUB_TRIGGER_CONFIG?.AUTHORIZE_ENDPOINT.includes(
                'https://github.com/',
              )
            }
          >
            Enterprise
          </Conditional>{' '}
          repository{' '}
          <LinkOrPlainText href={trigger.repository_url}>
            {trigger?.config?.build_source}
          </LinkOrPlainText>
        </>
      );
    case 'bitbucket':
      return (
        <>
          push to BitBucket repository{' '}
          <LinkOrPlainText href={trigger.repository_url}>
            {trigger?.config?.build_source}
          </LinkOrPlainText>
        </>
      );
    case 'gitlab':
      return (
        <>
          <GitlabIcon /> push to GitLab repository{' '}
          <LinkOrPlainText href={trigger.repository_url}>
            {trigger?.config?.build_source}
          </LinkOrPlainText>
        </>
      );
    case 'custom-git':
      return <>push to repository {trigger?.config?.build_source}</>;
    default:
      return <></>;
  }
}
