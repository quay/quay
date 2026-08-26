import {
  Alert,
  Button,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';
import {useEffect} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useDeleteCollaborator} from 'src/hooks/UseMembers';
import {IMembers} from 'src/resources/MembersResource';

export default function CollaboratorsDeleteModal(
  props: CollaboratorsDeleteModalProps,
) {
  const {addAlert} = useUI();
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
      props.toggleModal();
    }
  }, [errorDeleteCollaborator]);

  useEffect(() => {
    if (successDeleteCollaborator) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted collaborator`,
      });
      props.toggleModal();
    }
  }, [successDeleteCollaborator]);

  return (
    <Modal
      variant={ModalVariant.medium}
      isOpen={props.isModalOpen}
      onClose={props.toggleModal}
    >
      <ModalHeader
        title={'Remove user from organization'}
        titleIconVariant="warning"
        description={deleteAlert}
      />
      <ModalBody>
        Are you sure you want to delete <b> {props.collaborator.name} </b>?
      </ModalBody>
      <ModalFooter>
        <Button
          key="delete"
          variant="danger"
          onClick={() => {
            removeCollaborator({
              collaborator: props.collaborator.name,
            });
          }}
          data-testid={`${props.collaborator.name}-del-btn`}
        >
          Delete
        </Button>
        <Button key="cancel" variant="link" onClick={props.toggleModal}>
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );
}

interface CollaboratorsDeleteModalProps {
  isModalOpen: boolean;
  toggleModal: () => void;
  collaborator: IMembers;
  organizationName: string;
}
