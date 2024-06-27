import {Toolbar, ToolbarContent, ToolbarItem} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';

import {FilterInput} from 'src/components/toolbar/FilterInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ISuperuserOrgs} from 'src/hooks/UseSuperuserOrgs';

export function SuperuserOrgsToolBar(props: SuperuserOrgsToolBarProps) {
  return (
    <Toolbar>
      <ToolbarContent>
        <DropdownCheckbox
          selectedItems={props.selectedOrgs}
          deSelectAll={props.deSelectAll}
          allItemsList={props.allItems}
          itemsPerPageList={props.paginatedItems}
          onItemSelect={props.onItemSelect}
        />
        <FilterInput
          id="orgslist-search-input"
          searchState={props.search}
          onChange={props.setSearch}
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

type SuperuserOrgsToolBarProps = {
  selectedOrgs: ISuperuserOrgs[];
  deSelectAll: () => void;
  allItems: ISuperuserOrgs[];
  paginatedItems: ISuperuserOrgs[];
  onItemSelect: (
    item: ISuperuserOrgs,
    rowIndex: number,
    isSelecting: boolean,
  ) => void;
  search: SearchState;
  setSearch: (searchState) => void;
  perPage: number;
  page: number;
  setPage: (pageNumber) => void;
  setPerPage: (perPageNumber) => void;
};
