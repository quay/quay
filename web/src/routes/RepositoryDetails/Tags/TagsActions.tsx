import {
  Dropdown,
  DropdownItem,
  KebabToggle,
  DropdownPosition,
} from '@patternfly/react-core';
import {useState} from 'react';
import AddTagModal from './TagsActionsAddTagModal';
import EditLabelsModal from './TagsActionsLabelsModal';
import EditExpirationModal from './TagsActionsEditExpirationModal';
import {DeleteModal, ModalOptions} from './DeleteModal';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useSetRecoilState} from 'recoil';
import {selectedTagsState} from 'src/atoms/TagListState';

export default function TagActions(props: TagActionsProps) {
  const quayConfig = useQuayConfig();
  const [isOpen, setIsOpen] = useState(false);
  const [isAddTagModalOpen, setIsAddTagModalOpen] = useState(false);
  const [isEditLabelsModalOpen, setIsEditLabelsModalOpen] = useState(false);
  const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] =
    useState(false);
  const [deleteModalOptions, setDeleteModalOptions] = useState<ModalOptions>({
    isOpen: false,
    force: false,
  });
  const setSelectedTags = useSetRecoilState(selectedTagsState);

  const dropdownItems = [
    <DropdownItem
      key="add-tag-action"
      onClick={() => {
        setIsOpen(false);
        setIsAddTagModalOpen(true);
      }}
    >
      Add new tag
    </DropdownItem>,
    <DropdownItem
      key="edit-labels-action"
      onClick={() => {
        setIsOpen(false);
        setIsEditLabelsModalOpen(true);
      }}
    >
      Edit labels
    </DropdownItem>,
    <DropdownItem
      key="edit-expiration-action"
      onClick={() => {
        setIsOpen(false);
        setIsEditExpirationModalOpen(true);
      }}
    >
      Change expiration
    </DropdownItem>,
    <DropdownItem
      key="delete-tag-action"
      onClick={() => {
        setIsOpen(false);
        setDeleteModalOptions({
          force: false,
          isOpen: true,
        });
      }}
      style={{color: 'red'}}
    >
      Remove
    </DropdownItem>,
  ];

  if (
    quayConfig?.config?.PERMANENTLY_DELETE_TAGS &&
    props.repoDetails?.tag_expiration_s > 0
  ) {
    dropdownItems.push(
      <DropdownItem
        key="permanentlydelete"
        onClick={() => {
          setIsOpen(false);
          setDeleteModalOptions({
            force: true,
            isOpen: true,
          });
        }}
        style={{color: 'red'}}
      >
        Permanently Delete
      </DropdownItem>,
    );
  }

  return (
    <>
      <Dropdown
        toggle={
          <KebabToggle
            id="tag-actions-kebab"
            onToggle={(isOpen: boolean) => setIsOpen(isOpen)}
          />
        }
        isOpen={isOpen}
        isPlain
        position={DropdownPosition.right}
        dropdownItems={dropdownItems}
      />
      <AddTagModal
        org={props.org}
        repo={props.repo}
        isOpen={isAddTagModalOpen}
        setIsOpen={setIsAddTagModalOpen}
        manifest={props.manifest}
        loadTags={props.loadTags}
        onComplete={() => setSelectedTags([])}
      />
      <EditLabelsModal
        org={props.org}
        repo={props.repo}
        manifest={props.manifest}
        isOpen={isEditLabelsModalOpen}
        setIsOpen={setIsEditLabelsModalOpen}
        onComplete={() => {
          setSelectedTags([]);
          setIsEditLabelsModalOpen(false);
        }}
      />
      <EditExpirationModal
        org={props.org}
        repo={props.repo}
        isOpen={isEditExpirationModalOpen}
        setIsOpen={setIsEditExpirationModalOpen}
        tags={props.tags}
        expiration={props.expiration}
        loadTags={props.loadTags}
        onComplete={() => setSelectedTags([])}
      />
      <DeleteModal
        modalOptions={deleteModalOptions}
        setModalOptions={setDeleteModalOptions}
        tags={props.tags}
        org={props.org}
        repo={props.repo}
        loadTags={props.loadTags}
        repoDetails={props.repoDetails}
        onComplete={() => setSelectedTags([])}
      />
    </>
  );
}

interface TagActionsProps {
  org: string;
  repo: string;
  tags: string[];
  expiration: string;
  manifest: string;
  loadTags: () => void;
  repoDetails: RepositoryDetails;
}
