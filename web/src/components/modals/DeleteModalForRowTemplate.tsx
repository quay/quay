import {Button, Modal, ModalVariant} from '@patternfly/react-core';

export default function DeleteModalForRowTemplate<T, K extends keyof T>(
  props: DeleteModalForRowTemplateProps<T, K>,
) {
  return (
    <Modal
      variant={ModalVariant.medium}
      title={`${props.deleteMsgTitle}`}
      titleIconVariant="warning"
      isOpen={props.isModalOpen}
      onClose={props.toggleModal}
      actions={[
        <Button
          key="delete"
          variant="danger"
          onClick={() => {
            props.deleteHandler(props.itemToBeDeleted);
          }}
          data-testid={`${props.itemToBeDeleted[props.keyToDisplay]}-del-btn`}
        >
          Delete
        </Button>,
        <Button key="cancel" variant="link" onClick={props.toggleModal}>
          Cancel
        </Button>,
      ]}
    >
      Are you sure you want to delete{' '}
      <b> {props.itemToBeDeleted[props.keyToDisplay]} </b> ?
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
