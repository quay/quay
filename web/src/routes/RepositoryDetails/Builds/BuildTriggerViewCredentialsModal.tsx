import {
  Alert,
  Button,
  ClipboardCopy,
  List,
  ListItem,
  Modal,
  ModalVariant,
} from '@patternfly/react-core';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';

export default function BuildTriggerViewCredentialsModal(
  props: BuildTriggerViewCredentialsModalProps,
) {
  return (
    <Modal
      id="build-trigger-view-credentials-modal"
      title="Trigger Credentials"
      isOpen={props.isOpen}
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      actions={[
        <Button key="cancel" variant="primary" onClick={() => props.onClose()}>
          Done
        </Button>,
      ]}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      <Message service={props.trigger?.service} />
      <br />
      {props.trigger?.config?.credentials?.map((cred) => {
        return (
          <div key={cred?.name} data-testid={cred?.name}>
            {cred?.name}:<ClipboardCopy isReadOnly>{cred?.value}</ClipboardCopy>
          </div>
        );
      })}
    </Modal>
  );
}

function Message({service}: {service: string}) {
  switch (service) {
    case 'github':
    case 'bitbucket':
    case 'gitlab':
      return (
        <Alert variant="info" truncateTitle={1} title="">
          <p>
            The following key has been automatically added to your source
            control repository.
          </p>
        </Alert>
      );
    case 'custom-git':
      return (
        <Alert variant="info" truncateTitle={1} title="">
          <p>
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
          </p>
        </Alert>
      );
  }
}

interface BuildTriggerViewCredentialsModalProps {
  trigger: RepositoryBuildTrigger;
  isOpen: boolean;
  onClose: () => void;
}
