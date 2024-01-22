import {Toolbar, ToolbarContent, ToolbarItem} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {Kebab} from 'src/components/toolbar/Kebab';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';

import * as React from 'react';
import {FilterInput} from 'src/components/toolbar/FilterInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';

export function OrganizationToolBar(props: OrganizationToolBarProps) {
  return (
    <Toolbar>
      <ToolbarContent>
        <DropdownCheckbox
          selectedItems={props.selectedOrganization}
          deSelectAll={props.setSelectedOrganization}
          allItemsList={props.organizationsList}
          itemsPerPageList={props.paginatedOrganizationsList}
          onItemSelect={props.onSelectOrganization}
        />
        <FilterInput
          id="orgslist-search-input"
          searchState={props.search}
          onChange={props.setSearch}
        />
        <ToolbarButton
          id="create-organization-button"
          buttonValue="Create Organization"
          Modal={props.createOrgModal}
          isModalOpen={props.isOrganizationModalOpen}
          setModalOpen={props.setOrganizationModalOpen}
        />
        <ToolbarItem>
          {props.selectedOrganization?.length !== 0 ? (
            <Kebab
              isKebabOpen={props.isKebabOpen}
              setKebabOpen={props.setKebabOpen}
              kebabItems={props.kebabItems}
              useActions={true}
            />
          ) : null}
          {props.deleteKebabIsOpen ? props.deleteModal : null}
        </ToolbarItem>
        <ToolbarPagination
          itemsList={props.organizationsList}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
        />
      </ToolbarContent>
    </Toolbar>
  );
}

type OrganizationToolBarProps = {
  createOrgModal: object;
  isOrganizationModalOpen: boolean;
  setOrganizationModalOpen: (open) => void;
  isKebabOpen: boolean;
  setKebabOpen: (open) => void;
  kebabItems: React.ReactElement[];
  selectedOrganization: any[];
  deleteKebabIsOpen: boolean;
  deleteModal: object;
  organizationsList: any[];
  perPage: number;
  page: number;
  setPage: (pageNumber) => void;
  setPerPage: (perPageNumber) => void;
  total: number;
  search: SearchState;
  setSearch: (searchState) => void;
  setSelectedOrganization: (selectedOrgList) => void;
  paginatedOrganizationsList: any[];
  onSelectOrganization: (Org, rowIndex, isSelecting) => void;
};
