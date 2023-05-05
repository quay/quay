import {
  Flex,
  FlexItem,
  PanelFooter,
  Toolbar,
  ToolbarContent,
} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {ITeamMember} from 'src/hooks/UseMembers';

export default function ManageMembersToolbar(props: ManageMembersToolbarProps) {
  return (
    <>
      <Toolbar>
        <ToolbarContent>
          <DropdownCheckbox
            selectedItems={props.selectedTeams}
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
              />
            </FlexItem>
          </Flex>
          <ToolbarPagination
            itemsList={props.paginatedItems}
            perPage={props.perPage}
            page={props.page}
            setPage={props.setPage}
            setPerPage={props.setPerPage}
          />
        </ToolbarContent>
      </Toolbar>
      {props.children}
      <PanelFooter>
        <ToolbarPagination
          itemsList={props.paginatedItems}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
          bottom={true}
        />
      </PanelFooter>
    </>
  );
}

interface ManageMembersToolbarProps {
  selectedTeams: ITeamMember[];
  deSelectAll: () => void;
  allItems: ITeamMember[];
  paginatedItems: ITeamMember[];
  onItemSelect: (
    item: ITeamMember,
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
  children?: React.ReactNode;
}
