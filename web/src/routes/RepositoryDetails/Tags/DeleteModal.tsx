import {
  Modal,
  ModalVariant,
  Button,
  Label,
  Alert,
} from '@patternfly/react-core';
import {useEffect} from 'react';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import './Tags.css';
import {isNullOrUndefined} from 'src/libs/utils';
import Conditional from 'src/components/empty/Conditional';
import {useDeleteTag} from 'src/hooks/UseTags';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertDetails, AlertVariant} from 'src/atoms/AlertState';

export interface ModalOptions {
  isOpen: boolean;
  force: boolean;
}

export function DeleteModal(props: ModalProps) {
  const {
    deleteTags,
    successDeleteTags,
    errorDeleteTags,
    errorDeleteTagDetails,
  } = useDeleteTag(props.org, props.repo);
  const {addAlert} = useAlerts();
  const isReadonly: boolean = props.repoDetails?.state !== 'NORMAL';

  useEffect(() => {
    if (successDeleteTags) {
      props.loadTags();
      props.setModalOptions({
        force: false,
        isOpen: false,
      });
      if (!isNullOrUndefined(props.onComplete)) {
        props.onComplete();
      }
      const alert: AlertDetails = {
        variant: AlertVariant.Success,
        title: '',
      };
      switch (true) {
        case props.tags.length === 1 && props.modalOptions.force:
          alert.title = `Permanently deleted tag ${props.tags[0]} successfully`;
          break;
        case props.tags.length === 1 && !props.modalOptions.force:
          alert.title = `Deleted tag ${props.tags[0]} successfully`;
          break;
        case props.tags.length > 1 && props.modalOptions.force:
          alert.title = 'Permanently deleted tags successfully';
          break;
        case props.tags.length > 1 && !props.modalOptions.force:
          alert.title = `Deleted tags successfully`;
          break;
      }
      if (props.tags.length > 1) {
        alert.message = `Tags deleted: ${props.tags.join(', ')}`;
      }
      addAlert(alert);
    }
  }, [successDeleteTags]);

  useEffect(() => {
    if (errorDeleteTags) {
      const alert: AlertDetails = {
        variant: AlertVariant.Failure,
        title: '',
      };
      switch (true) {
        case props.tags.length === 1 && props.modalOptions.force:
          alert.title = `Could not permanently delete tag ${props.tags[0]}`;
          break;
        case props.tags.length === 1 && !props.modalOptions.force:
          alert.title = `Could not delete tag ${props.tags[0]}`;
          break;
        case props.tags.length > 1 && props.modalOptions.force:
          alert.title = 'Could not permanently delete tags';
          break;
        case props.tags.length > 1 && !props.modalOptions.force:
          alert.title = `Could not delete tags`;
          break;
      }
      alert.message = (
        <>
          {Array.from(errorDeleteTagDetails.getErrors()).map(([tag, error]) => (
            <p key={tag}>
              Could not delete tag {tag}: {error.error.message}
            </p>
          ))}
        </>
      );
      addAlert(alert);
    }
  }, [errorDeleteTags]);

  const title = props.modalOptions.force
    ? `Permanently delete the following tag(s)?`
    : `Delete the following tag(s)?`;
  return (
    <>
      <Modal
        id="tag-deletion-modal"
        title={title}
        description={
          <Conditional if={props.modalOptions.force}>
            <span style={{color: 'red'}}>
              Tags deleted cannot be restored within the time machine window and
              will be immediately eligible for garbage collection.
            </span>
          </Conditional>
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
            onClick={() =>
              deleteTags({tags: props.tags, force: props.modalOptions.force})
            }
            isDisabled={isReadonly}
          >
            Delete
          </Button>,
        ]}
      >
        <Conditional if={isReadonly}>
          <Alert
            id="form-error-alert"
            isInline
            variant="danger"
            title={`Repository is currently in ${props.repoDetails?.state} state. Deletion is disabled.`}
          />
          <div className="delete-modal-readonly-alert" />
        </Conditional>
        {props.tags?.map((tag) => (
          <span key={tag}>
            <Label>{tag}</Label>{' '}
          </span>
        ))}
        <Conditional if={props.tags?.length > 20}>
          <div>
            <b>Note:</b> This operation can take several minutes.
          </div>
        </Conditional>
      </Modal>
    </>
  );
}

type ModalProps = {
  modalOptions: ModalOptions;
  setModalOptions: (modalOptions) => void;
  tags: string[];
  onComplete?: () => void;
  loadTags: () => void;
  org: string;
  repo: string;
  repoDetails: RepositoryDetails;
};
