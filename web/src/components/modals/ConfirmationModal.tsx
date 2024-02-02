import {setRepositoryVisibility} from 'src/resources/RepositoryResource';
import {Modal, ModalVariant, Button} from '@patternfly/react-core';
import {useState} from 'react';
import FormError from 'src/components/errors/FormError';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useQueryClient} from '@tanstack/react-query';

export function ConfirmationModal(props: ConfirmationModalProps) {
  const [err, setErr] = useState<string>();

  const queryClient = useQueryClient();
  const changeVisibility = async () => {
    const visibility = props.makePublic ? 'public' : 'private';
    try {
      // TODO: Could replace this with a 'bulkSetRepoVisibility'
      // function in RepositoryResource in the future
      await Promise.all(
        props.selectedItems.map(async (item) => {
          const [org, ...repoArray] = item.split('/');
          const repo = repoArray.join('/');
          await setRepositoryVisibility(org, repo, visibility);
        }),
      );
      queryClient.invalidateQueries(['organization']);
      props.toggleModal();
      props.selectAllRepos(false);
    } catch (error: any) {
      console.error(error);
      setErr(addDisplayError('Unable to change visibility', error));
    }
  };

  const handleModalConfirm = async () => {
    if (props.handleModalConfirm) {
      props.handleModalConfirm();
      return;
    }
    // This modal should never render if no items have been selected,
    // that should be handled by the parent component. Leaving this check
    // in anyway.
    if (props.selectedItems.length > 0) {
      await changeVisibility();
    } else {
      setErr('No items selected');
    }
  };

  return (
    <Modal
      variant={ModalVariant.small}
      title={props.title}
      isOpen={props.modalOpen}
      onClose={props.toggleModal}
      actions={[
        <Button key="confirm" variant="primary" onClick={handleModalConfirm}>
          {props.buttonText}
        </Button>,
        <Button key="cancel" variant="link" onClick={props.toggleModal}>
          Cancel
        </Button>,
      ]}
    >
      <FormError message={err} setErr={setErr} />
      {props.description}
    </Modal>
  );
}

type ConfirmationModalProps = {
  title: string;
  description: string;
  modalOpen: boolean;
  buttonText: string;
  toggleModal: () => void;
  selectedItems?: string[];
  makePublic?: boolean;
  selectAllRepos?: (isSelecting) => void;
  handleModalConfirm?: () => void;
};
