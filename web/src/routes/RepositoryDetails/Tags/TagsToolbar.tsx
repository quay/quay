import {ReactElement, useState} from 'react';
import {
  DropdownItem,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {useRecoilState} from 'recoil';
import {searchTagsState, selectedTagsState} from 'src/atoms/TagListState';
import {Tag} from 'src/resources/TagResource';
import {DeleteModal, DeleteModalOptions} from './DeleteModal';
import {ImmutableModal, ImmutableModalOptions} from './ImmutableModal';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {Kebab} from 'src/components/toolbar/Kebab';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import ColumnNames from './ColumnNames';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import EditExpirationModal from './TagsActionsEditExpirationModal';
import {FilterInput} from 'src/components/toolbar/FilterInput';


export function TagsToolbar(props: ToolBarProps) {
  const quayConfig = useQuayConfig();
  const [deleteModalOptions, setDeleteModalOptions] = useState<DeleteModalOptions>({
    isOpen: false,
    force: false,
  });
  const [immutableModalOptions, setImmutableModalOptions] = useState<ImmutableModalOptions>({
    isOpen: false,
    force: false,
    immutable: false,
  });
  const [selectedTags, setSelectedTags] = useRecoilState(selectedTagsState);
  const [search, setSearch] = useRecoilState<SearchState>(searchTagsState);
  const [isEditExpirationModalOpen, setIsEditExpirationModalOpen] =
    useState(false);
  const [isKebabOpen, setKebabOpen] = useState(false);
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
        setDeleteModalOptions((prevOptions) => ({
          ...prevOptions,
          isOpen: !prevOptions.isOpen,
        }));
      }}
      isDisabled={selectedTags.length <= 0 || selectedTags.some((tag: Tag) => tag.immutable)}      
      className='dangerous-dropdown-item'
    >
      Remove
    </DropdownItem>,
    <DropdownItem
    key="immutable"
    onClick={() => {
      setKebabOpen(!isKebabOpen);
      setImmutableModalOptions((prevOptions) => ({
        ...prevOptions,
        isOpen: !prevOptions.isOpen,
        immutable: true,
      }));
    }}
    isDisabled={selectedTags.length <= 0 || selectedTags.every((tag: Tag) => tag.immutable) || selectedTags.some((tag: Tag) => tag.expiration)}
  >
    Set immutable
  </DropdownItem>,
  <DropdownItem
  key="mutable"
  onClick={() => {
    setKebabOpen(!isKebabOpen);
    setImmutableModalOptions((prevOptions) => ({
      ...prevOptions,
      isOpen: !prevOptions.isOpen,
      immutable: false,
    }));
  }}
  isDisabled={selectedTags.length <= 0 || selectedTags.every((tag: Tag) => tag.immutable == false)}
>
  Set mutable
</DropdownItem>,
  ];

  if (
    quayConfig?.config?.PERMANENTLY_DELETE_TAGS &&
    props.repoDetails?.tag_expiration_s > 0
  ) {
    kebabItems.push(
      <DropdownItem
        key="permanentlydelete"
        onClick={() => {
          setKebabOpen(!isKebabOpen);
          setDeleteModalOptions((prevOptions) => ({
            force: true,
            isOpen: !prevOptions.isOpen,
          }));
        }}
        isDisabled={selectedTags.length <= 0 || selectedTags.some((tag: Tag) => tag.immutable)}
        className='dangerous-dropdown-item'
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
          {selectedTags?.length !== 0 ? (
            <Kebab
              isKebabOpen={isKebabOpen}
              setKebabOpen={setKebabOpen}
              kebabItems={kebabItems}
              useActions={true}
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
        modalOptions={deleteModalOptions}
        setModalOptions={setDeleteModalOptions}
        tags={selectedTags}
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
        loadTags={props.loadTags}
        onComplete={() => {
          setSelectedTags([]);
        }}
      />
      <ImmutableModal
        modalOptions={immutableModalOptions}
        setModalOptions={setImmutableModalOptions}
        selectedTags={selectedTags}
        setSelectedTags={setSelectedTags}
        org={props.organization}
        repo={props.repository}
        loadTags={props.loadTags}
        repoDetails={props.repoDetails}
        immutability={immutableModalOptions.immutable}
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
