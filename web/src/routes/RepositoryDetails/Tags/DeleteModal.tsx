import {
  Modal,
  ModalVariant,
  Button,
  Label,
  Alert,
} from '@patternfly/react-core';
import {useState} from 'react';
import ErrorModal from 'src/components/errors/ErrorModal';
import {addDisplayError, BulkOperationError} from 'src/resources/ErrorHandling';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {bulkDeleteTags} from 'src/resources/TagResource';
import './Tags.css';

export interface ModalOptions {
  isOpen: boolean;
  force: boolean;
}

export function DeleteModal(props: ModalProps) {
  const [err, setErr] = useState<string[]>();
  const isReadonly: boolean = props.repoDetails?.state !== 'NORMAL';

  const deleteTags = async () => {
    try {
      const tags = props.selectedTags.map((tag) => ({
        org: props.org,
        repo: props.repo,
        tag: tag,
      }));
      await bulkDeleteTags(tags, props.modalOptions.force);
    } catch (err: any) {
      console.error(err);
      if (err instanceof BulkOperationError) {
        const errMessages = [];
        // TODO: Would like to use for .. of instead of foreach
        // typescript complains saying we're using version prior to es6?
        err.getErrors().forEach((error, tag) => {
          errMessages.push(
            addDisplayError(`Failed to delete tag ${tag}`, error.error),
          );
        });
        setErr(errMessages);
      } else {
        setErr([addDisplayError('Failed to delete tags', err)]);
      }
    } finally {
      props.loadTags();
      props.setModalOptions((prevOptions) => ({
        force: false,
        isOpen: !prevOptions.isOpen,
      }));
      props.setSelectedTags([]);
    }
  };
  const title = props.modalOptions.force
    ? `Permanently delete the following tag${
        props.selectedTags.length > 1 ? 's' : ''
      }?`
    : `Delete the following tag${props.selectedTags.length > 1 ? 's' : ''}?`;
  return (
    <>
      <ErrorModal title="Tag deletion failed" error={err} setError={setErr} />
      <Modal
        id="tag-deletion-modal"
        title={title}
        description={
          props.modalOptions.force ? (
            <span style={{color: 'red'}}>
              Tags deleted cannot be restored within the time machine window and
              will be immediately eligible for garbage collection.
            </span>
          ) : (
            ''
          )
        }
        isOpen={props.modalOptions.isOpen}
        disableFocusTrap={true}
        key="modal"
        onClose={() => {
          props.setModalOptions((prevOptions) => ({
            force: false,
            isOpen: !prevOptions.isOpen,
          }));
        }}
        data-testid="delete-tags-modal"
        variant={ModalVariant.small}
        actions={[
          <Button
            key="cancel"
            variant="primary"
            onClick={() => {
              props.setModalOptions((prevOptions) => ({
                force: false,
                isOpen: !prevOptions.isOpen,
              }));
            }}
          >
            Cancel
          </Button>,
          <Button
            key="modal-action-button"
            variant="primary"
            onClick={deleteTags}
            isDisabled={isReadonly}
          >
            Delete
          </Button>,
        ]}
      >
        {isReadonly ? (
          <>
            <Alert
              id="form-error-alert"
              isInline
              variant="danger"
              title={`Repository is currently in ${props.repoDetails?.state} state. Deletion is disabled.`}
            />
            <div className="delete-modal-readonly-alert" />
          </>
        ) : null}

        {props.selectedTags.map((tag) => (
          <span key={tag}>
            <Label>{tag}</Label>{' '}
          </span>
        ))}
        {props.selectedTags.length > 10 ? (
          <div>
            <b>Note:</b> This operation can take several minutes.
          </div>
        ) : null}
      </Modal>
    </>
  );
}

type ModalProps = {
  modalOptions: ModalOptions;
  setModalOptions: (modalOptions) => void;
  selectedTags: string[];
  setSelectedTags: (selectedTags: string[]) => void;
  loadTags: () => void;
  org: string;
  repo: string;
  repoDetails: RepositoryDetails;
};
