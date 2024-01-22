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
import {FilterInput} from 'src/components/toolbar/FilterInput';

export function TagsToolbar(props: ToolBarProps) {
  const quayConfig = useQuayConfig();
  const [modalOptions, setModalOptions] = useState<ModalOptions>({
    isOpen: false,
    force: false,
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
        modalOptions={modalOptions}
        setModalOptions={setModalOptions}
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
