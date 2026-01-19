import {useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import AddTagModal from './TagsActionsAddTagModal';
import EditLabelsModal from './TagsActionsLabelsModal';
import EditExpirationModal from './TagsActionsEditExpirationModal';
import ImmutabilityModal from './TagsActionsImmutabilityModal';
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
  const [isImmutabilityModalOpen, setIsImmutabilityModalOpen] = useState(false);
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
      isDisabled={props.isImmutable}
      tooltipProps={
        props.isImmutable
          ? {content: 'Cannot change expiration of immutable tag'}
          : undefined
      }
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
      isDisabled={props.isImmutable}
      tooltipProps={
        props.isImmutable ? {content: 'Cannot delete immutable tag'} : undefined
      }
      style={{color: props.isImmutable ? undefined : 'red'}}
    >
      Remove
    </DropdownItem>,
  ];

  // Add immutability toggle action if feature is enabled
  if (quayConfig?.features?.IMMUTABLE_TAGS) {
    // Only show "Remove immutability" if user has admin permission
    const showRemoveImmutability =
      props.isImmutable && props.repoDetails?.can_admin;
    const showMakeImmutable = !props.isImmutable;

    if (showMakeImmutable || showRemoveImmutability) {
      // Insert before the delete action (at position -2 to be before delete items)
      dropdownItems.splice(
        -1, // Insert before last item (Remove)
        0,
        <DropdownItem
          key="toggle-immutability"
          onClick={() => {
            setIsOpen(false);
            setIsImmutabilityModalOpen(true);
          }}
          data-testid="toggle-immutability-action"
        >
          {props.isImmutable ? 'Remove immutability' : 'Make immutable'}
        </DropdownItem>,
      );
    }
  }

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
        isDisabled={props.isImmutable}
        tooltipProps={
          props.isImmutable
            ? {content: 'Cannot permanently delete immutable tag'}
            : undefined
        }
        style={{color: props.isImmutable ? undefined : 'red'}}
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
        popperProps={{
          enableFlip: true,
          position: 'center',
        }}
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
      <ImmutabilityModal
        org={props.org}
        repo={props.repo}
        isOpen={isImmutabilityModalOpen}
        setIsOpen={setIsImmutabilityModalOpen}
        tags={props.tags}
        currentlyImmutable={props.isImmutable || false}
        loadTags={props.loadTags}
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
  isImmutable?: boolean;
}
