import {
  Alert,
  Button,
  Label,
  Modal,
  ModalVariant,
} from '@patternfly/react-core';
import {useEffect} from 'react';
import {AlertDetails, AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useSetTagsImmutability} from 'src/hooks/UseTags';
import {isNullOrUndefined} from 'src/libs/utils';
import {getDisplayError} from 'src/resources/ErrorHandling';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {Tag} from 'src/resources/TagResource';
import './Tags.css';

export interface ImmutableModalOptions {
  isOpen: boolean;
  immutable: boolean;
}

export function ImmutableModal(props: ImmutableModalProps) {
  const {addAlert} = useAlerts();
  const isReadonly: boolean = props.repoDetails?.state !== 'NORMAL';

  const {setTagImmutability, success, error, errorDetails} =
    useSetTagsImmutability(props.org, props.repo);

  useEffect(() => {
    if (error) {
      const alert: AlertDetails = {
        variant: AlertVariant.Failure,
        title: '',
      };

      switch (true) {
        case props.selectedTags.length === 1:
          alert.title = `Failed to set tag ${props.selectedTags[0].name} to ${
            props.immutability ? 'immutable' : 'mutable'
          }`;
          break;
        case props.selectedTags.length > 1:
          alert.title = `Failed to set tags to ${
            props.immutability ? 'immutable' : 'mutable'
          }`;
          break;
      }
      alert.message = (
        <>
          {Array.from(errorDetails.getErrors()).map(([tag, error]) => (
            <p key={tag}>
              Failed to set tag {tag} to{' '}
              {props.immutability ? 'immutable' : 'mutable'}:{' '}
              {getDisplayError(error)}
            </p>
          ))}
        </>
      );
      addAlert(alert);
    }
  }, [error]);

  useEffect(() => {
    if (success) {
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
        case props.selectedTags.length === 1:
          alert.title = `Set tag ${props.selectedTags[0].name} to ${
            props.immutability ? 'immutable' : 'mutable'
          }`;
          break;
        case props.selectedTags.length > 1:
          alert.title = `Set tags to ${
            props.immutability ? 'immutable' : 'mutable'
          }`;
          break;
      }
      if (props.selectedTags.length > 1) {
        alert.message = `Tags set to ${
          props.immutability ? 'immutable' : 'mutable'
        }: ${props.selectedTags.map((tag) => tag.name).join(', ')}`;
      }
      addAlert(alert);
    }
  }, [success]);

  const title = `Set the following tag${
    props.selectedTags.length > 1 ? 's' : ''
  } to ${props.immutability ? 'immutable' : 'mutable'} ?`;
  return (
    <>
      <Modal
        id="tag-immutability-modal"
        title={title}
        titleIconVariant={props.immutability ? 'warning' : 'info'}
        description={
          props.immutability ? (
            <span>
              This will prevent tags from being deleted, overwritten, expire or
              restored to until it is made mutable again. Immutable tags cannot
              have their manifests labels changed. Manifests, that have
              immutable tags pointing to them cannot be deleted. Only repository
              administrators can make tags mutable again.
            </span>
          ) : (
            'This will allow the tags to be deleted, overwritten, expire or restored to.'
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
        data-testid="immutable-tags-modal"
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
              setTagImmutability({
                tags: props.selectedTags,
                immutable: props.immutability,
              })
            }
            isDisabled={isReadonly}
          >
            Set {props.immutability ? 'immutable' : 'mutable'}
          </Button>,
        ]}
      >
        {isReadonly ? (
          <>
            <Alert
              id="form-error-alert"
              isInline
              variant="danger"
              title={`Repository is currently in ${props.repoDetails?.state} state. Changing tag mutability is disabled.`}
            />
            <div className="immutable-modal-readonly-alert" />
          </>
        ) : null}

        {props.selectedTags.map((tag) => (
          <span key={tag.name}>
            <Label>{tag.name}</Label>{' '}
          </span>
        ))}
        {props.selectedTags.length > 10 ? (
          <div>
            <b>Note:</b> This operation can take a couple of moments.
          </div>
        ) : null}
      </Modal>
    </>
  );
}

type ImmutableModalProps = {
  modalOptions: ImmutableModalOptions;
  setModalOptions: (modalOptions) => void;
  immutability: boolean;
  selectedTags: Tag[];
  setSelectedTags: (selectedTags: Tag[]) => void;
  repoDetails: RepositoryDetails;
  loadTags: () => void;
  org: string;
  repo: string;
  onComplete?: () => void;
};
