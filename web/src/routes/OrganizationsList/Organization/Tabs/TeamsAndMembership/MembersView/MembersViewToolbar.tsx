import {Flex, FlexItem, Toolbar, ToolbarContent} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {IMembers} from 'src/resources/MembersResource';

export default function MembersViewToolbar(props: MembersViewToolbarProps) {
  return (
    <Toolbar>
      <ToolbarContent>
        <DropdownCheckbox
          selectedItems={props.selectedMembers}
          deSelectAll={props.deSelectAll}
          allItemsList={props.allItems}
          itemsPerPageList={props.paginatedItems}
          onItemSelect={props.onItemSelect}
        />
        <SearchDropdown
          items={props.searchOptions}
          searchState={props.search}
          setSearchState={props.setSearch}
        />
        <Flex className="pf-u-mr-md">
          <FlexItem>
            <SearchInput
              searchState={props.search}
              onChange={props.setSearch}
              id="members-view-search"
            />
          </FlexItem>
        </Flex>
        <ToolbarPagination
          itemsList={props.allItems}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
        />
      </ToolbarContent>
    </Toolbar>
  );
}

interface MembersViewToolbarProps {
  selectedMembers: IMembers[];
  deSelectAll: () => void;
  allItems: IMembers[];
  paginatedItems: IMembers[];
  onItemSelect: (
    item: IMembers,
    rowIndex: number,
    isSelecting: boolean,
  ) => void;
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  searchOptions: string[];
  search: SearchState;
  setSearch: (search: SearchState) => void;
}
