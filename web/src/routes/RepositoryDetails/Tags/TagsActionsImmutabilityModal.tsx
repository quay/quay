import {
  Alert,
  Button,
  Modal,
  ModalVariant,
  TextContent,
  Text,
} from '@patternfly/react-core';
import {useEffect} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useSetTagImmutability} from 'src/hooks/UseTags';
import {isNullOrUndefined} from 'src/libs/utils';

export default function ImmutabilityModal(props: ImmutabilityModalProps) {
  const {addAlert} = useUI();
  const {
    setImmutability,
    successSetImmutability,
    errorSetImmutability,
    errorSetImmutabilityDetails,
  } = useSetTagImmutability(props.org, props.repo);

  useEffect(() => {
    if (successSetImmutability) {
      const action = props.currentlyImmutable ? 'removed' : 'set';
      const title =
        props.tags.length === 1
          ? `Successfully ${action} immutability for tag ${props.tags[0]}`
          : `Successfully ${action} immutability for ${props.tags.length} tags`;
      addAlert({variant: AlertVariant.Success, title: title});
      props.loadTags();
      props.setIsOpen(false);
      if (!isNullOrUndefined(props.onComplete)) {
        props.onComplete();
      }
    }
  }, [successSetImmutability]);

  useEffect(() => {
    if (errorSetImmutability) {
      const action = props.currentlyImmutable ? 'remove' : 'set';
      const title =
        props.tags.length === 1
          ? `Could not ${action} immutability for tag ${props.tags[0]}`
          : `Could not ${action} immutability for tags`;
      const errorDisplayMessage = errorSetImmutabilityDetails ? (
        <>
          {Array.from(errorSetImmutabilityDetails.getErrors()).map(
            ([tag, error]) => (
              <p key={tag}>
                Could not update immutability for tag {tag}:{' '}
                {error.error.message}
              </p>
            ),
          )}
        </>
      ) : null;
      addAlert({
        variant: AlertVariant.Failure,
        title: title,
        message: errorDisplayMessage,
      });
      props.setIsOpen(false);
      if (!isNullOrUndefined(props.onComplete)) {
        props.onComplete();
      }
    }
  }, [errorSetImmutability]);

  const onConfirm = () => {
    setImmutability({tags: props.tags, immutable: !props.currentlyImmutable});
  };

  const onClose = () => {
    props.setIsOpen(false);
  };

  const tagCount = props.tags.length;
  const tagWord = tagCount === 1 ? 'tag' : 'tags';
  const title = props.currentlyImmutable
    ? `Remove immutability from ${tagCount} ${tagWord}?`
    : `Make ${tagCount} ${tagWord} immutable?`;

  const description = props.currentlyImmutable
    ? `Removing immutability will allow ${
        tagCount === 1 ? 'this tag' : 'these tags'
      } to be modified or deleted.`
    : `Making ${tagCount === 1 ? 'a tag' : 'tags'} immutable prevents ${
        tagCount === 1 ? 'it' : 'them'
      } from being modified or deleted. Admin permission will be required to remove immutability.`;

  const confirmButtonText = props.currentlyImmutable
    ? 'Remove immutability'
    : 'Make immutable';

  return (
    <Modal
      id="immutability-modal"
      data-testid="immutability-modal"
      title={title}
      isOpen={props.isOpen}
      onClose={onClose}
      variant={ModalVariant.small}
      actions={[
        <Button key="cancel" variant="link" onClick={onClose}>
          Cancel
        </Button>,
        <Button
          key="confirm"
          variant="primary"
          onClick={onConfirm}
          data-testid="confirm-immutability-btn"
        >
          {confirmButtonText}
        </Button>,
      ]}
    >
      {props.tagsWithExpiration && props.tagsWithExpiration.length > 0 && (
        <>
          <Alert
            isInline
            variant="warning"
            title="Tags with expiration will be skipped"
            data-testid="expiring-tags-immutability-warning"
          >
            The following tags have expiration dates and cannot be made
            immutable. Clear their expiration first:{' '}
            {props.tagsWithExpiration.join(', ')}
          </Alert>
          <div style={{marginBottom: '1rem'}} />
        </>
      )}
      <TextContent>
        <Text>{description}</Text>
      </TextContent>
    </Modal>
  );
}

interface ImmutabilityModalProps {
  org: string;
  repo: string;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  tags: string[];
  currentlyImmutable: boolean;
  loadTags: () => void;
  onComplete?: () => void;
  tagsWithExpiration?: string[];
}
