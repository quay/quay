import {
  Button,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  TextInput,
  Title,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useCreateTag} from 'src/hooks/UseTags';
import {isNullOrUndefined, validateTagName} from 'src/libs/utils';

type validate = 'success' | 'error' | 'default';

export default function AddTagModal(props: AddTagModalProps) {
  const [value, setValue] = useState('');
  const {addAlert} = useUI();
  const {createTag, successCreateTag, errorCreateTag} = useCreateTag(
    props.org,
    props.repo,
  );

  // determine tag validity
  const isValid = value !== '' ? validateTagName(value) : false;
  const validatedState =
    value === '' ? 'default' : isValid ? 'success' : 'error';

  // centrallized closing handle
  const handleClose = () => {
    setValue('');
    props.setIsOpen(false);
    if (!isNullOrUndefined(props.onComplete)) {
      props.onComplete();
    }
  };

  useEffect(() => {
    if (successCreateTag) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully created tag ${value}`,
      });
      props.loadTags();
      handleClose();
    }
  }, [successCreateTag]);

  useEffect(() => {
    if (errorCreateTag) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Could not create tag ${value}`,
      });
      handleClose();
    }
  }, [errorCreateTag]);

  return (
    <>
      <Modal
        id="add-tag-modal"
        aria-label="Add tag modal"
        isOpen={props.isOpen}
        onClose={handleClose}
        variant={ModalVariant.small}
      >
        <ModalHeader
          title={`Add tag to manifest ${props.manifest.substring(0, 19)}`}
        />
        <ModalBody>
          <TextInput
            id="tag-form-name"
            value={value}
            type="text"
            validated={validatedState}
            onChange={(_event, value) => {
              setValue(value);
            }}
            aria-label="new tag name"
            placeholder="New tag name"
            aria-describedby="tag-name-helper"
            aria-invalid={validatedState === 'error'}
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem
                id="tag-name-helper"
                variant={validatedState}
                {...(validatedState === 'error' && {
                  icon: <ExclamationCircleIcon />,
                })}
              >
                {validatedState === 'error'
                  ? 'Must start with a letter, digit or underscore. Only letters, digits, underscores, hyphens and periods allowed. Max 128 characters.'
                  : 'Enter a tag name'}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </ModalBody>
        <ModalFooter>
          <Button
            key="modal-action-button"
            isDisabled={!isValid}
            variant="primary"
            onClick={() => {
              createTag({tag: value, manifest: props.manifest});
            }}
          >
            Create tag
          </Button>
          <Button key="cancel" variant="link" onClick={handleClose}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}

interface AddTagModalProps {
  org: string;
  repo: string;
  isOpen: boolean;
  manifest: string;
  setIsOpen: (open: boolean) => void;
  loadTags: () => void;
  onComplete?: () => void;
}
