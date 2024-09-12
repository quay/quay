import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import {useState} from 'react';
import {useSetRecoilState} from 'recoil';
import {selectedTagsState} from 'src/atoms/TagListState';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {Tag} from 'src/resources/TagResource';
import {DeleteModal, DeleteModalOptions} from './DeleteModal';
import {ImmutableModal, ImmutableModalOptions} from './ImmutableModal';
import AddTagModal from './TagsActionsAddTagModal';
import EditExpirationModal from './TagsActionsEditExpirationModal';
import EditLabelsModal from './TagsActionsLabelsModal';

export default function TagActions(props: TagActionsProps) {
  const quayConfig = useQuayConfig();
  const [isOpen, setIsOpen] = useState(false);
  const [isAddTagModalOpen, setIsAddTagModalOpen] = useState(false);
  const [isEditLabelsModalOpen, setIsEditLabelsModalOpen] = useState(false);
  const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] =
    useState(false);
  const [deleteModalOptions, setDeleteModalOptions] =
    useState<DeleteModalOptions>({
      isOpen: false,
      force: false,
    });
  const [immutableModalOptions, setImmutableModalOptions] =
    useState<ImmutableModalOptions>({
      isOpen: false,
      immutable: false,
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
      isDisabled={props.tags.some((tag: Tag) => tag.immutable)}
      onClick={() => {
        setIsOpen(false);
        setIsEditLabelsModalOpen(true);
      }}
    >
      Edit labels
    </DropdownItem>,
    <DropdownItem
      key="edit-expiration-action"
      isDisabled={props.tags.some((tag: Tag) => tag.immutable)}
      onClick={() => {
        setIsOpen(false);
        setIsEditExpirationModalOpen(true);
      }}
    >
      Change expiration
    </DropdownItem>,
    <DropdownItem
      key="mutable"
      onClick={() => {
        setIsOpen(false);
        setImmutableModalOptions((prevOptions) => ({
          ...prevOptions,
          isOpen: !prevOptions.isOpen,
          immutable: props.tags.some((tag: Tag) => tag.immutable)
            ? false
            : true,
        }));
      }}
    >
      {props.tags.some((tag: Tag) => tag.immutable)
        ? 'Set mutable'
        : 'Set immutable'}
    </DropdownItem>,
  ];

  dropdownItems.push(
    <DropdownItem
      key="delete-tag-action"
      isDisabled={props.tags.some((tag: Tag) => tag.immutable)}
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
  );

  if (
    quayConfig?.config?.PERMANENTLY_DELETE_TAGS &&
    props.repoDetails?.tag_expiration_s > 0
  ) {
    dropdownItems.push(
      <DropdownItem
        key="permanentlydelete"
        isDisabled={props.tags.some((tag: Tag) => tag.immutable)}
        onClick={() => {
          setIsOpen(false);
          setDeleteModalOptions({
            force: true,
            isOpen: true,
          });
        }}
        style={{color: 'red'}}
      >
        Permanently delete
      </DropdownItem>,
    );
  }

  return (
    <>
      <Dropdown
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            id="tag-actions-kebab"
            aria-label="Tag actions kebab"
            variant="plain"
            onClick={() => setIsOpen(() => !isOpen)}
            isExpanded={isOpen}
          >
            <EllipsisVIcon />
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>{dropdownItems}</DropdownList>
      </Dropdown>
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
      <ImmutableModal
        modalOptions={immutableModalOptions}
        setModalOptions={setImmutableModalOptions}
        selectedTags={props.tags}
        setSelectedTags={setSelectedTags}
        org={props.org}
        repo={props.repo}
        loadTags={props.loadTags}
        repoDetails={props.repoDetails}
        immutability={immutableModalOptions.immutable}
        onComplete={() => setSelectedTags([])}
      />
    </>
  );
}

interface TagActionsProps {
  org: string;
  repo: string;
  tags: Tag[];
  expiration: string;
  manifest: string;
  loadTags: () => void;
  repoDetails: RepositoryDetails;
}
