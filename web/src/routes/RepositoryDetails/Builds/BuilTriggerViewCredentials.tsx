import {Alert, ClipboardCopy, List, ListItem} from '@patternfly/react-core';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';

export default function ViewCredentials(props: ViewCredentialsProps) {
  return (
    <>
      <Message service={props.trigger?.service} />
      <br />
      {props.trigger?.config?.credentials?.map((cred) => {
        return (
          <div key={cred?.name} data-testid={cred?.name}>
            {cred?.name}:<ClipboardCopy isReadOnly>{cred?.value}</ClipboardCopy>
          </div>
        );
      })}
    </>
  );
}

function Message({service}: {service: string}) {
  switch (service) {
    case 'github':
    case 'bitbucket':
    case 'gitlab':
      return (
        <Alert
          variant="info"
          title="The following key has been automatically added to your source control repository."
        />
      );
    case 'custom-git':
      return (
        <Alert variant="info" title="Note:">
          In order to use this trigger, the following first requires action:
          <List>
            <ListItem style={{marginTop: '0'}}>
              You must give the following public key read access to the git
              repository.
            </ListItem>
            <ListItem style={{marginTop: '0'}}>
              You must set your repository to POST to the following URL to
              trigger a build.
            </ListItem>
          </List>
          For more information, refer to the{' '}
          <a
            href="https://docs.projectquay.io/use_quay.html#setting-up-custom-git-trigger"
            target="_blank"
            rel="noreferrer"
          >
            Custom Git Triggers documentation
          </a>
          .
        </Alert>
      );
  }
}

interface ViewCredentialsProps {
  trigger: RepositoryBuildTrigger;
}
