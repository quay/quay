import {
  Button,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';

export default function DeleteModalForRowTemplate<T, K extends keyof T>(
  props: DeleteModalForRowTemplateProps<T, K>,
) {
  return (
    <Modal
      variant={ModalVariant.medium}
      isOpen={props.isModalOpen}
      onClose={props.toggleModal}
    >
      <ModalHeader
        title={`${props.deleteMsgTitle}`}
        titleIconVariant="warning"
      />
      <ModalBody>
        Are you sure you want to delete{' '}
        <b> {props.itemToBeDeleted[props.keyToDisplay]} </b> ?
      </ModalBody>
      <ModalFooter>
        <Button
          key="delete"
          variant="danger"
          onClick={() => {
            props.deleteHandler(props.itemToBeDeleted);
          }}
          data-testid={`${props.itemToBeDeleted[props.keyToDisplay]}-del-btn`}
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

interface DeleteModalForRowTemplateProps<T, K> {
  deleteMsgTitle: string;
  isModalOpen: boolean;
  toggleModal: () => void;
  deleteHandler: (item: T | T[]) => void;
  itemToBeDeleted: T;
  keyToDisplay: K;
}
