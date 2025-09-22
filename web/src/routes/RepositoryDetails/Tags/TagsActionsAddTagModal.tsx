import {
  Alert,
  Button,
  Modal,
  ModalVariant,
  Spinner,
  TextInput,
  Title,
} from '@patternfly/react-core';
import {useCallback, useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useCreateTag} from 'src/hooks/UseTags';
import {isNullOrUndefined} from 'src/libs/utils';
import {getTags} from 'src/resources/TagResource';

// Simple debounce function
function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number,
): T {
  let timeout: NodeJS.Timeout;
  return ((...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  }) as T;
}

export default function AddTagModal(props: AddTagModalProps) {
  const [value, setValue] = useState('');
  const [existingTagInfo, setExistingTagInfo] = useState<{
    exists: boolean;
    manifest?: string;
  } | null>(null);
  const [isCheckingTag, setIsCheckingTag] = useState(false);
  const {addAlert} = useAlerts();
  const {createTag, successCreateTag, errorCreateTag} = useCreateTag(
    props.org,
    props.repo,
  );

  // Function to check if tag exists
  const checkTagExists = async (tagName: string) => {
    if (!tagName.trim()) {
      setExistingTagInfo(null);
      return;
    }

    setIsCheckingTag(true);
    try {
      // Call existing tags API to check if tag exists
      const tagsResponse = await getTags(
        props.org,
        props.repo,
        1,
        50,
        tagName,
        true,
      );
      const existingTag = tagsResponse.tags.find(
        (tag) => tag.name === tagName,
      );

      if (existingTag) {
        setExistingTagInfo({
          exists: true,
          manifest: existingTag.manifest_digest,
        });
      } else {
        setExistingTagInfo({exists: false});
      }
    } catch (error) {
      setExistingTagInfo({exists: false});
    } finally {
      setIsCheckingTag(false);
    }
  };

  // Debounce the check to avoid too many API calls
  const debouncedCheckTag = useCallback(
    debounce((tagName: string) => checkTagExists(tagName), 500),
    [props.org, props.repo],
  );

  useEffect(() => {
    if (successCreateTag) {
      const actionType = existingTagInfo?.exists ? 'moved' : 'created';
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully ${actionType} tag ${value}`,
      });
      setValue('');
      setExistingTagInfo(null);
      props.loadTags();
      props.setIsOpen(false);
      if (!isNullOrUndefined(props.onComplete)) {
        props.onComplete();
      }
    }
  }, [successCreateTag, existingTagInfo]);

  useEffect(() => {
    if (errorCreateTag) {
      const actionType = existingTagInfo?.exists ? 'move' : 'create';
      addAlert({
        variant: AlertVariant.Failure,
        title: `Could not ${actionType} tag ${value}`,
      });
      setValue('');
      setExistingTagInfo(null);
      props.setIsOpen(false);
      if (!isNullOrUndefined(props.onComplete)) {
        props.onComplete();
      }
    }
  }, [errorCreateTag, existingTagInfo]);

  return (
    <>
      <Modal
        id="add-tag-modal"
        header={
          <Title headingLevel="h2">
            {existingTagInfo?.exists ? 'Move' : 'Add'} tag to manifest {props.manifest.substring(0, 19)}
          </Title>
        }
        aria-label="Add tag modal"
        isOpen={props.isOpen}
        onClose={() => props.setIsOpen(false)}
        variant={ModalVariant.small}
        actions={[
          <Button
            key="cancel"
            variant="primary"
            onClick={() => props.setIsOpen(false)}
          >
            Cancel
          </Button>,
          <Button
            key="modal-action-button"
            variant="primary"
            isDisabled={isCheckingTag || !value.trim()}
            onClick={() => {
              createTag({tag: value, manifest: props.manifest});
            }}
          >
            {existingTagInfo?.exists ? 'Move Tag' : 'Create Tag'}
          </Button>,
        ]}
      >
        <TextInput
          value={value}
          type="text"
          onChange={(_event, value) => {
            setValue(value);
            debouncedCheckTag(value);
          }}
          aria-label="new tag name"
          placeholder="New tag name"
        />
        {isCheckingTag && (
          <div style={{marginTop: '16px'}}>
            <Spinner size="sm" /> Checking tag availability...
          </div>
        )}
        {existingTagInfo?.exists && (
          <Alert
            variant="warning"
            title={`${value} is already applied to another image. This will move the tag.`}
            style={{marginTop: '16px'}}
          />
        )}
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
