import {
  Button,
  Flex,
  FlexItem,
  PanelFooter,
  Toolbar,
  ToolbarContent,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {ITeamMember, ITeamMembersCanSyncResponse} from 'src/hooks/UseMembers';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';

export default function ManageMembersToolbar(props: ManageMembersToolbarProps) {
  return (
    <>
      <Toolbar id="team-members-toolbar">
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
                id="team-member-search-input"
                searchState={props.search}
                onChange={props.setSearch}
              />
            </FlexItem>
          </Flex>
          <Flex>
            <Conditional
              if={
                props.isAdmin && !props.isReadOnly && !props.pageInReadOnlyMode
              }
            >
              <FlexItem>
                <Button
                  onClick={() =>
                    props.setDrawerContent(
                      OrganizationDrawerContentType.AddNewTeamMemberDrawer,
                    )
                  }
                  data-testid="add-new-member-btn"
                >
                  Add new member
                </Button>
              </FlexItem>
            </Conditional>

            <Conditional
              if={
                props.displaySyncDirectory &&
                props.teamCanSync?.service == 'oidc'
              }
            >
              <FlexItem>
                <Button onClick={props.toggleOIDCTeamSyncModal}>
                  Enable Team Sync
                </Button>
              </FlexItem>
            </Conditional>

            <Conditional
              if={props.pageInReadOnlyMode && props.teamCanSync != null}
            >
              <FlexItem>
                <Button onClick={props.toggleRemoveTeamSyncModal}>
                  Remove synchronization
                </Button>
              </FlexItem>
            </Conditional>
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
  setDrawerContent: (content: OrganizationDrawerContentType) => void;
  isReadOnly: boolean;
  isAdmin: boolean;
  displaySyncDirectory: boolean;
  isOIDCTeamSyncModalOpen: boolean;
  toggleOIDCTeamSyncModal: () => void;
  teamCanSync?: ITeamMembersCanSyncResponse;
  pageInReadOnlyMode: boolean;
  isRemoveTeamSyncModalOpen: boolean;
  toggleRemoveTeamSyncModal: () => void;
}
