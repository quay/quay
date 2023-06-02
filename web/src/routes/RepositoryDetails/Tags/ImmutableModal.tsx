import {
  Modal,
  ModalVariant,
  Button,
  Label,
  Alert,
} from '@patternfly/react-core';
import {useState} from 'react';
import ErrorModal from 'src/components/errors/ErrorModal';
import {DeleteModalOptions, DeleteModalProps} from './DeleteModal';
import {addDisplayError, BulkOperationError} from 'src/resources/ErrorHandling';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {Tag, setTagsMutability} from 'src/resources/TagResource';
import './Tags.css';


export interface ImmutableModalOptions extends DeleteModalOptions {
  immutable: boolean;
}

export function ImmutableModal(props: ImmutableModalProps) {
  const [err, setErr] = useState<string[]>();
  const isReadonly: boolean = props.repoDetails?.state !== 'NORMAL';

  const immutableTags = async () => {
    try {
      const tags = props.selectedTags.map((tag) => ({
        org: props.org,
        repo: props.repo,
        tag: tag.name,
      }));
      await setTagsMutability(tags, props.immutability);
    } catch (err: any) {
      console.error(err);
      if (err instanceof BulkOperationError) {
        const errMessages = [];
        // TODO: Would like to use for .. of instead of foreach
        // typescript complains saying we're using version prior to es6?
        err.getErrors().forEach((error, tag) => {
          errMessages.push(
            addDisplayError(`Failed to set tag ${tag} to ` + (props.immutability ? 'immutable' : 'mutable'), error.error),
          );
        });
        setErr(errMessages);
      } else {
        setErr([addDisplayError('Failed to set tags to '+ (props.immutability ? 'immutable' : 'mutable'), err)]);
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
  const title = `Set the following tag${props.selectedTags.length > 1 ? 's' : ''} to ${props.immutability ? 'immutable' : 'mutable'} ?`;
  return (
    <>
      <ErrorModal title="Changing tag mutability failed" error={err} setError={setErr} />
      <Modal
        id="tag-immutability-modal"
        title={title}
        titleIconVariant={props.immutability ? 'warning' : 'info'}
        description={
          props.immutability ? (
            <span>
              This will prevent tags from being deleted, overwritten, expire or restored to until it is made mutable again.
              Immutable tags cannot have their manifests labels changed.
              Manifests, that have immutable tags pointing to them cannot be deleted.
              Only repository administrators can make tags mutable again.
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
            onClick={immutableTags}
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
};