import {Alert, Button, Modal, ModalVariant} from '@patternfly/react-core';
import {useEffect} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useDeleteCollaborator} from 'src/hooks/UseMembers';
import {IMembers} from 'src/resources/MembersResource';

export default function CollaboratorsDeleteModal(
  props: CollaboratorsDeleteModalProps,
) {
  const {addAlert} = useAlerts();
  const deleteMsg =
    'User will be removed from all teams and repositories under this organization in which they are a member or have permissions.';
  const deleteAlert = (
    <Alert variant="warning" title={deleteMsg} ouiaId="WarningAlert" />
  );

  const {
    removeCollaborator,
    errorDeleteCollaborator,
    successDeleteCollaborator,
  } = useDeleteCollaborator(props.organizationName);

  useEffect(() => {
    if (errorDeleteCollaborator) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Error deleting collaborator`,
      });
    }
  }, [errorDeleteCollaborator]);

  useEffect(() => {
    if (successDeleteCollaborator) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted collaborator`,
      });
    }
  }, [successDeleteCollaborator]);

  return (
    <Modal
      variant={ModalVariant.medium}
      title={'Remove user from organization'}
      titleIconVariant="warning"
      description={deleteAlert}
      isOpen={props.isModalOpen}
      onClose={props.toggleModal}
      actions={[
        <Button
          key="delete"
          variant="danger"
          onClick={() => {
            removeCollaborator({
              collaborator: props.collaborator.name,
            });
            props.toggleModal;
          }}
          data-testid={`${props.collaborator.name}-del-btn`}
        >
          Delete
        </Button>,
        <Button key="cancel" variant="link" onClick={props.toggleModal}>
          Cancel
        </Button>,
      ]}
    >
      Are you sure you want to delete <b> {props.collaborator.name} </b>?
    </Modal>
  );
}

interface CollaboratorsDeleteModalProps {
  isModalOpen: boolean;
  toggleModal: () => void;
  collaborator: IMembers;
  organizationName: string;
}
