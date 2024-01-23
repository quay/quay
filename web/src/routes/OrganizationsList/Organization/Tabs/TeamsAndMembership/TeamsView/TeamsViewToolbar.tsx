import {
  Flex,
  FlexItem,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Button,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {Kebab} from 'src/components/toolbar/Kebab';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {ITeams} from 'src/hooks/UseTeams';

export default function TeamsViewToolbar(props: TeamsViewToolbarProps) {
  return (
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
        <Flex className="pf-v5-u-mr-md">
          <FlexItem>
            <SearchInput
              searchState={props.search}
              onChange={props.setSearch}
              id="teams-view-search"
            />
          </FlexItem>
        </Flex>
        <ToolbarItem>
          <Conditional if={props.isAdmin && !props.isReadOnly}>
            <Button
              onClick={() => props.handleModalToggle()}
              data-testid="create-new-team-button"
            >
              Create new team
            </Button>
          </Conditional>
        </ToolbarItem>
        <ToolbarItem>
          <Conditional
            if={
              props.selectedTeams?.length !== 0 &&
              props.isAdmin &&
              !props.isReadOnly
            }
          >
            <Kebab
              isKebabOpen={props.isKebabOpen}
              setKebabOpen={props.setKebabOpen}
              kebabItems={props.kebabItems}
              useActions={true}
            />
          </Conditional>
          <Conditional if={props.deleteKebabIsOpen}>
            {props.deleteModal}
          </Conditional>
          <Conditional if={props.isSetRepoPermModalOpen}>
            {props.setRepoPermModal}
          </Conditional>
        </ToolbarItem>
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

interface TeamsViewToolbarProps {
  selectedTeams: ITeams[];
  deSelectAll: () => void;
  allItems: ITeams[];
  paginatedItems: ITeams[];
  onItemSelect: (item: ITeams, rowIndex: number, isSelecting: boolean) => void;
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  searchOptions: string[];
  search: SearchState;
  setSearch: (search: SearchState) => void;
  isKebabOpen: boolean;
  setKebabOpen: (open: boolean) => void;
  kebabItems: React.ReactElement[];
  deleteKebabIsOpen: boolean;
  deleteModal: object;
  isSetRepoPermModalOpen: boolean;
  setRepoPermModal: object;
  handleModalToggle: () => void;
  isReadOnly: boolean;
  isAdmin: boolean;
}
