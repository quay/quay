import {
  Alert,
  Button,
  Modal,
  ModalVariant,
  Title,
} from '@patternfly/react-core';
import {LoadingPage} from 'src/components/LoadingPage';
import RequestError from 'src/components/errors/RequestError';
import {useFetchBuildTrigger} from 'src/hooks/UseBuildTriggers';
import BuildTriggerSetupWizard from './BuildTriggerSetupWizard';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {useState} from 'react';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';
import {isNullOrUndefined} from 'src/libs/utils';
import ViewCredentials from './BuilTriggerViewCredentials';

export default function SetupBuildTriggerModal(props: SetupBuildTriggerWizard) {
  const {trigger, isLoading, isError, error} = useFetchBuildTrigger(
    props.org,
    props.repo,
    props.triggerUuid,
  );
  const [updatedTrigger, setUpdatedTrigger] =
    useState<RepositoryBuildTrigger>(null);

  let modalContent = null;

  if (isLoading) {
    modalContent = <LoadingPage />;
  } else if (isError) {
    modalContent = <RequestError message={error as string} />;
  } else if (trigger.is_active) {
    modalContent = (
      <div style={{padding: '2em'}}>
        <Alert
          variant="info"
          title="Trigger setup has already been completed"
          ouiaId="InfoAlert"
        />
        <br />
        <Button onClick={props.onClose}>Close</Button>
      </div>
    );
  } else if (!isNullOrUndefined(updatedTrigger) && updatedTrigger.is_active) {
    modalContent = (
      <div style={{padding: '2em'}}>
        <Title headingLevel="h3">Trigger has been successfully activated</Title>
        <br />
        <Alert
          variant="warning"
          title={
            <>
              <strong>Please note:</strong> If the trigger continuously fails to
              build, it will be automatically disabled. It can be re-enabled
              from the build trigger list.
            </>
          }
        />
        <br />
        <ViewCredentials trigger={updatedTrigger} />
        <br />
        <Button onClick={props.onClose}>Close</Button>
      </div>
    );
  } else {
    modalContent = (
      <BuildTriggerSetupWizard
        org={props.org}
        repo={props.repo}
        trigger={trigger}
        isOpen={props.isOpen}
        onClose={props.onClose}
        isOrganization={props.repoDetails.is_organization}
        setUpdatedTrigger={setUpdatedTrigger}
      />
    );
  }

  return (
    <Modal
      id="create-robot-account-modal"
      aria-label="CreateRobotAccount"
      variant={ModalVariant.large}
      isOpen={props.isOpen}
      onClose={props.onClose}
      showClose={true}
      hasNoBodyWrapper
    >
      {modalContent}
    </Modal>
  );
}

interface SetupBuildTriggerWizard {
  org: string;
  repo: string;
  isOpen: boolean;
  onClose: () => void;
  triggerUuid: string;
  repoDetails: RepositoryDetails;
}
