import {GithubIcon, GitlabIcon} from '@patternfly/react-icons';
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
          repository <a>{trigger?.config?.build_source}</a>
        </>
      );
    case 'bitbucket':
      return (
        <>
          push to BitBucket repository <a>{trigger?.config?.build_source}</a>
        </>
      );
    case 'gitlab':
      return (
        <>
          <GitlabIcon /> push to GitLab repository{' '}
          <a>{trigger?.config?.build_source}</a>
        </>
      );
    case 'custom-git':
      return (
        <>
          push to repository <a>{trigger?.config?.build_source}</a>
        </>
      );
    default:
      return <></>;
  }
}
