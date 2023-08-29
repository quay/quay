import {
  DropdownItem,
  Flex,
  FlexItem,
  PanelFooter,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {Kebab} from 'src/components/toolbar/Kebab';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {ITeamRepoPerms} from 'src/hooks/UseTeams';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';

export default function SetRepoPermissionsForTeamModalToolbar(
  props: SetRepoPermissionsForTeamModalToolbarProps,
) {
  const dropdownOnSelect = (selectedVal) => {
    props.selectedRepoPerms.map((repoPerm) => {
      props.updateModifiedRepoPerms(selectedVal?.toLowerCase(), repoPerm);
    });
  };

  return (
    <>
      <Toolbar>
        <ToolbarContent>
          <DropdownCheckbox
            selectedItems={props.selectedRepoPerms}
            deSelectAll={props.deSelectAll}
            allItemsList={props.allItems}
            itemsPerPageList={props.paginatedItems}
            onItemSelect={props.onItemSelect}
            id="add-repository-bulk-select"
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
                id="set-repo-perm-for-team-search"
              />
            </FlexItem>
          </Flex>
          <ToolbarItem>
            <Conditional if={props.selectedRepoPerms?.length > 0}>
              <Kebab
                isKebabOpen={props.isKebabOpen}
                setKebabOpen={props.setKebabOpen}
                kebabItems={RepoPermissionDropdownItems.map((item) => (
                  <DropdownItem
                    key={item.name}
                    description={item.description}
                    onClick={() => dropdownOnSelect(item.name)}
                  >
                    {item.name}
                  </DropdownItem>
                ))}
                useActions={false}
                id="toggle-bulk-perms-kebab"
              />
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
      {props.children}
      <PanelFooter>
        <ToolbarPagination
          itemsList={props.allItems}
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

interface SetRepoPermissionsForTeamModalToolbarProps {
  selectedRepoPerms: ITeamRepoPerms[];
  deSelectAll: () => void;
  allItems: ITeamRepoPerms[];
  paginatedItems: ITeamRepoPerms[];
  onItemSelect: (
    item: ITeamRepoPerms,
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
  isKebabOpen: boolean;
  setKebabOpen: (open: boolean) => void;
  updateModifiedRepoPerms: (item, repoPerm) => void;
}
