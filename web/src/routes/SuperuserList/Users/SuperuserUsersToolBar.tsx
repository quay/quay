import {Toolbar, ToolbarContent, ToolbarItem} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {Kebab} from 'src/components/toolbar/Kebab';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';

import * as React from 'react';
import {FilterInput} from 'src/components/toolbar/FilterInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ISuperuserUsers} from 'src/hooks/UseSuperuserUsers';
import Conditional from 'src/components/empty/Conditional';

export function SuperuserUsersToolBar(props: SuperuserUsersToolBarProps) {
  return (
    <Toolbar>
      <ToolbarContent>
        <DropdownCheckbox
          selectedItems={props.selectedUsers}
          deSelectAll={props.deSelectAll}
          allItemsList={props.allItems}
          itemsPerPageList={props.paginatedItems}
          onItemSelect={props.onItemSelect}
        />
        <FilterInput
          id="userslist-search-input"
          searchState={props.search}
          onChange={props.setSearch}
        />
        <ToolbarButton
          id="create-user-button"
          buttonValue="Create User"
          Modal={props.createUserModal}
          isModalOpen={props.isUserModalOpen}
          setModalOpen={props.setUserModalOpen}
        />
        <ToolbarItem>
          {/* <Conditional if={props.selectedUsers?.length !== 0}>
            <Kebab
              isKebabOpen={props.isKebabOpen}
              setKebabOpen={props.setKebabOpen}
              kebabItems={props.kebabItems}
              useActions={true}
            />
          </Conditional>
          <Conditional if={props.deleteKebabIsOpen}>
            {props.deleteModal}
          </Conditional> */}
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

type SuperuserUsersToolBarProps = {
  selectedUsers: ISuperuserUsers[];
  deSelectAll: () => void;
  allItems: ISuperuserUsers[];
  paginatedItems: ISuperuserUsers[];
  onItemSelect: (
    item: ISuperuserUsers,
    rowIndex: number,
    isSelecting: boolean,
  ) => void;
  search: SearchState;
  setSearch: (searchState) => void;
  createUserModal: object;
  isUserModalOpen: boolean;
  setUserModalOpen: (open) => void;
  perPage: number;
  page: number;
  setPage: (pageNumber) => void;
  setPerPage: (perPageNumber) => void;
};
