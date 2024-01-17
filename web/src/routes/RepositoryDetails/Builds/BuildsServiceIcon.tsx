import {GithubIcon, GitlabIcon} from '@patternfly/react-icons';

export default function ServiceIcon(props: ServiceIconProps) {
  switch (props.service) {
    case 'github':
      return <GithubIcon />;
    case 'bitbucket':
      return <></>; // Need icon for bitbucket
    case 'gitlab':
      return <GitlabIcon />;
    default:
      return <></>;
  }
}

interface ServiceIconProps {
  service: string;
}
