import {
  DropdownItem,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {ReactElement, useState} from 'react';
import {useRecoilState} from 'recoil';
import {searchTagsState, selectedTagsState} from 'src/atoms/TagListState';
import {Tag} from 'src/resources/TagResource';
import {DeleteModal} from './DeleteModal';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {Kebab} from 'src/components/toolbar/Kebab';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import ColumnNames from './ColumnNames';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {RepositoryDetails} from 'src/resources/RepositoryResource';

export function TagsToolbar(props: ToolBarProps) {
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [selectedTags, setSelectedTags] = useRecoilState(selectedTagsState);
  const [search, setSearch] = useRecoilState<SearchState>(searchTagsState);

  const [isKebabOpen, setKebabOpen] = useState(false);
  const kebabItems: ReactElement[] = [
    <DropdownItem
      key="delete"
      onClick={() => {
        setKebabOpen(!isKebabOpen);
        setIsModalOpen(!isModalOpen);
      }}
      isDisabled={selectedTags.length <= 0}
    >
      Delete
    </DropdownItem>,
  ];

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
          items={[ColumnNames.name, ColumnNames.manifest]}
        />
        <SearchInput
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
        isOpen={isModalOpen}
        setIsOpen={setIsModalOpen}
        selectedTags={selectedTags}
        setSelectedTags={setSelectedTags}
        org={props.organization}
        repo={props.repository}
        loadTags={props.loadTags}
        repoDetails={props.repoDetails}
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
