import {ReactElement, useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuItem,
  MenuToggle,
  MenuToggleElement,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {CogIcon} from '@patternfly/react-icons';
import {useRecoilState} from 'recoil';
import {
  searchTagsState,
  selectedTagsState,
  showSignaturesState,
  expandedViewState,
} from 'src/atoms/TagListState';
import {Tag} from 'src/resources/TagResource';
import {DeleteModal, ModalOptions} from './DeleteModal';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {Kebab} from 'src/components/toolbar/Kebab';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import ColumnNames from './ColumnNames';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import EditExpirationModal from './TagsActionsEditExpirationModal';
import ImmutabilityModal from './TagsActionsImmutabilityModal';
import {FilterInput} from 'src/components/toolbar/FilterInput';

export function TagsToolbar(props: ToolBarProps) {
  const quayConfig = useQuayConfig();
  const [modalOptions, setModalOptions] = useState<ModalOptions>({
    isOpen: false,
    force: false,
  });
  const [selectedTags, setSelectedTags] = useRecoilState(selectedTagsState);
  const [search, setSearch] = useRecoilState<SearchState>(searchTagsState);
  const [showSignatures, setShowSignatures] =
    useRecoilState(showSignaturesState);
  const [expandedView, setExpandedView] = useRecoilState(expandedViewState);
  const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] =
    useState(false);
  const [isImmutabilityModalOpen, setIsImmutabilityModalOpen] = useState(false);
  const [isKebabOpen, setKebabOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Filter selected tags to get only mutable ones for bulk immutability
  const selectedMutableTags = selectedTags.filter((tagName) => {
    const tag = props.TagList.find((t) => t.name === tagName);
    return tag && !tag.immutable;
  });

  // Filter selected tags to get immutable ones for delete warning
  const selectedImmutableTags = selectedTags.filter((tagName) => {
    const tag = props.TagList.find((t) => t.name === tagName);
    return tag && tag.immutable;
  });

  // Check if immutable tags can expire
  const canImmutableTagsExpire =
    quayConfig?.config?.FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE ?? false;

  // Filter mutable tags that have expiration (can't be made immutable when config disallows)
  const selectedMutableTagsWithExpiration = canImmutableTagsExpire
    ? []
    : selectedMutableTags.filter((tagName) => {
        const tag = props.TagList.find((t) => t.name === tagName);
        return tag && tag.expiration;
      });

  // Mutable tags without expiration (or all if config allows expiration)
  const selectedMutableTagsForImmutability = canImmutableTagsExpire
    ? selectedMutableTags
    : selectedMutableTags.filter((tagName) => {
        const tag = props.TagList.find((t) => t.name === tagName);
        return tag && !tag.expiration;
      });

  const kebabItems: ReactElement[] = [
    <DropdownItem
      key="set-expiration"
      onClick={() => {
        setKebabOpen(!isKebabOpen);
        setIsEditExpirationModalOpen(true);
      }}
      isDisabled={selectedTags.length <= 0}
    >
      Set expiration
    </DropdownItem>,
    <DropdownItem
      key="delete"
      onClick={() => {
        setKebabOpen(!isKebabOpen);
        setModalOptions((prevOptions) => ({
          ...prevOptions,
          isOpen: !prevOptions.isOpen,
        }));
      }}
      isDisabled={selectedTags.length <= 0}
      style={{color: 'red'}}
    >
      Remove
    </DropdownItem>,
  ];

  // Add immutability action if feature is enabled
  if (quayConfig?.features?.IMMUTABLE_TAGS) {
    // Determine tooltip content
    let immutableTooltip: string | undefined;
    if (selectedTags.length > 0 && selectedMutableTags.length === 0) {
      immutableTooltip = 'All selected tags are already immutable';
    } else if (
      selectedMutableTags.length > 0 &&
      selectedMutableTagsForImmutability.length === 0 &&
      !canImmutableTagsExpire
    ) {
      immutableTooltip =
        'All selected mutable tags have expiration dates. Clear expiration first.';
    }

    kebabItems.splice(
      1, // Insert after "Set expiration"
      0,
      <DropdownItem
        key="make-immutable"
        onClick={() => {
          setKebabOpen(!isKebabOpen);
          setIsImmutabilityModalOpen(true);
        }}
        isDisabled={selectedMutableTagsForImmutability.length <= 0}
        tooltipProps={
          immutableTooltip ? {content: immutableTooltip} : undefined
        }
        data-testid="bulk-make-immutable-action"
      >
        Make immutable
      </DropdownItem>,
    );
  }

  if (
    quayConfig?.config?.PERMANENTLY_DELETE_TAGS &&
    props.repoDetails?.tag_expiration_s > 0
  ) {
    kebabItems.push(
      <DropdownItem
        key="permanentlydelete"
        onClick={() => {
          setKebabOpen(!isKebabOpen);
          setModalOptions((prevOptions) => ({
            force: true,
            isOpen: !prevOptions.isOpen,
          }));
        }}
        isDisabled={selectedTags.length <= 0}
        style={{color: 'red'}}
      >
        Permanently delete
      </DropdownItem>,
    );
  }

  return (
    <Toolbar>
      <ToolbarContent>
        <DropdownCheckbox
          selectedItems={selectedTags}
          deSelectAll={setSelectedTags}
          allItemsList={props.TagList}
          itemsPerPageList={props.paginatedTags}
          onItemSelect={props.selectTag}
        />
        <SearchDropdown
          searchState={search}
          setSearchState={setSearch}
          items={[ColumnNames.name, ColumnNames.digest]}
        />
        <FilterInput
          id="tagslist-search-input"
          searchState={search}
          onChange={setSearch}
        />
        <ToolbarItem>
          <Dropdown
            toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
              <MenuToggle
                ref={toggleRef}
                id="tags-settings-toggle"
                aria-label="Tags view settings"
                variant="plain"
                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                isExpanded={isSettingsOpen}
              >
                <CogIcon />
              </MenuToggle>
            )}
            isOpen={isSettingsOpen}
            onOpenChange={(isOpen) => setIsSettingsOpen(isOpen)}
            popperProps={{
              enableFlip: true,
              position: 'center',
              direction: 'up',
            }}
          >
            <DropdownList>
              <MenuItem
                itemId="expanded-view"
                description="Display additional tag details inline"
                hasCheckbox
                isSelected={expandedView}
                onClick={() => setExpandedView(!expandedView)}
              >
                Expanded View
              </MenuItem>
              <MenuItem
                itemId="show-signatures"
                description="Display cosign signature tags"
                hasCheckbox
                isSelected={showSignatures}
                onClick={() => setShowSignatures(!showSignatures)}
              >
                Show Signatures
              </MenuItem>
            </DropdownList>
          </Dropdown>
        </ToolbarItem>
        <ToolbarItem>
          {selectedTags?.length !== 0 ? (
            <Kebab
              isKebabOpen={isKebabOpen}
              setKebabOpen={setKebabOpen}
              kebabItems={kebabItems}
              useActions={true}
              data-testid="bulk-actions-kebab"
            />
          ) : null}
        </ToolbarItem>

        <ToolbarPagination
          itemsList={props.TagList}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
        />
      </ToolbarContent>
      <DeleteModal
        modalOptions={modalOptions}
        setModalOptions={setModalOptions}
        tags={selectedMutableTags}
        immutableTags={selectedImmutableTags}
        onComplete={() => {
          setSelectedTags([]);
        }}
        org={props.organization}
        repo={props.repository}
        loadTags={props.loadTags}
        repoDetails={props.repoDetails}
      />
      <EditExpirationModal
        org={props.organization}
        repo={props.repository}
        isOpen={isEditExpirationModalOpen}
        setIsOpen={setIsEditExpirationModalOpen}
        tags={selectedTags}
        immutableTags={canImmutableTagsExpire ? [] : selectedImmutableTags}
        loadTags={props.loadTags}
        onComplete={() => {
          setSelectedTags([]);
        }}
      />
      <ImmutabilityModal
        org={props.organization}
        repo={props.repository}
        isOpen={isImmutabilityModalOpen}
        setIsOpen={setIsImmutabilityModalOpen}
        tags={selectedMutableTagsForImmutability}
        tagsWithExpiration={selectedMutableTagsWithExpiration}
        currentlyImmutable={false}
        loadTags={props.loadTags}
        onComplete={() => {
          setSelectedTags([]);
        }}
      />
    </Toolbar>
  );
}

type ToolBarProps = {
  organization: string;
  repository: string;
  tagCount: number;
  loadTags: () => void;
  TagList: Tag[];
  paginatedTags: Tag[];
  perPage: number;
  page: number;
  setPage: (pageNumber) => void;
  setPerPage: (perPageNumber) => void;
  selectTag: (tag: Tag, rowIndex?: number, isSelecting?: boolean) => void;
  repoDetails: RepositoryDetails;
};
