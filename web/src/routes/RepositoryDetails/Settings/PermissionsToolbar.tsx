import {
  Button,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {useState} from 'react';
import Conditional from 'src/components/empty/Conditional';
import Menu from 'src/components/Table/Menu';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {SearchDropdown} from 'src/components/toolbar/SearchDropdown';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {RepoMember} from 'src/resources/RepositoryResource';
import {DrawerContentType} from '../Types';
import ChangePermissions from './PermissionsActionsChangePermissions';
import Delete from './PermissionsActionsDelete';

export default function PermissionsToolbar(props: PermissionsToolbarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState<boolean>(false);
  return (
    <Toolbar>
      <ToolbarContent>
        <DropdownCheckbox
          id="permissions-select-all"
          selectedItems={props.selectedItems}
          deSelectAll={props.deselectAll}
          allItemsList={props.allItems}
          itemsPerPageList={props.paginatedItems}
          onItemSelect={props.onItemSelect}
        />
        <SearchDropdown
          items={props.searchOptions}
          searchState={props.search}
          setSearchState={props.setSearch}
        />
        <SearchInput
          id="permissions-search-input"
          searchState={props.search}
          onChange={props.setSearch}
        />
        <ToolbarItem>
          <Button
            onClick={() =>
              props.setDrawerContent(DrawerContentType.AddPermission)
            }
          >
            Add permissions
          </Button>
        </ToolbarItem>
        <ToolbarItem>
          <Conditional if={props.selectedItems?.length > 0}>
            <Menu
              toggle="Actions"
              isOpen={isMenuOpen}
              setIsOpen={setIsMenuOpen}
              items={[
                <Delete
                  key="delete-action"
                  deselectAll={props.deselectAll}
                  org={props.org}
                  repo={props.repo}
                  selectedItems={props.selectedItems}
                  setIsMenuOpen={setIsMenuOpen}
                />,
                <ChangePermissions
                  key="change-permissions-action"
                  deselectAll={props.deselectAll}
                  org={props.org}
                  repo={props.repo}
                  selectedItems={props.selectedItems}
                  setIsMenuOpen={setIsMenuOpen}
                />,
              ]}
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
  );
}

interface PermissionsToolbarProps {
  org: string;
  repo: string;

  allItems: RepoMember[];
  paginatedItems: RepoMember[];
  selectedItems: RepoMember[];

  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;

  searchOptions: string[];
  search: SearchState;
  setSearch: (search: SearchState) => void;

  onItemSelect: (
    item: RepoMember,
    rowIndex: number,
    isSelecting: boolean,
  ) => void;
  deselectAll: () => void;
  setDrawerContent: (content: DrawerContentType) => void;
}
