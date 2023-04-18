import {Toolbar, ToolbarContent} from '@patternfly/react-core';
import {DropdownCheckbox} from 'src/components/toolbar/DropdownCheckbox';
import {IRobot} from 'src/resources/RobotsResource';
import {useRecoilState} from 'recoil';
import {searchRobotAccountState} from 'src/atoms/RobotAccountState';
import {FilterInput} from 'src/components/toolbar/FilterInput';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {Kebab} from 'src/components/toolbar/Kebab';
import React, {ReactElement} from 'react';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {ExpandCollapseButton} from 'src/components/toolbar/ExpandCollapseButton';
import {BulkDelete} from 'src/components/toolbar/BulkDelete';

export function RobotAccountsToolBar(props: RobotAccountsToolBarProps) {
  const [search, setSearch] = useRecoilState(searchRobotAccountState);

  return (
    <Toolbar>
      <ToolbarContent>
        <DropdownCheckbox
          selectedItems={props.selectedItems}
          deSelectAll={props.setSelectedRobotAccounts}
          allItemsList={props.allItemsList}
          itemsPerPageList={props.itemsPerPageList}
          onItemSelect={props.onItemSelect}
          id="robot-account-dropdown-checkbox"
        />
        <FilterInput
          searchState={search}
          onChange={setSearch}
          id="robot-account-search"
        />
        <ToolbarButton
          id="create-robot-account-btn"
          buttonValue={props.buttonText}
          Modal={props.pageModal}
          isModalOpen={props.isModalOpen}
          setModalOpen={props.setModalOpen}
        />
        <ExpandCollapseButton
          expandTable={props.expandTable}
          collapseTable={props.collapseTable}
        />
        {props.selectedItems.length > 0 ? (
          <BulkDelete setClicked={props.setDeleteModalOpen} />
        ) : null}
        {props.deleteKebabIsOpen ? props.deleteModal() : null}
        <ToolbarPagination
          itemsList={props.allItemsList}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
          total={props.total}
        />
      </ToolbarContent>
    </Toolbar>
  );
}

type RobotAccountsToolBarProps = {
  selectedItems: IRobot[];
  allItemsList: IRobot[];
  itemsPerPageList: IRobot[];
  setSelectedRobotAccounts: (selectedRobotAccounts) => void;
  onItemSelect: (Item, rowIndex, isSelecting) => void;
  buttonText: string;
  pageModal: object;
  isModalOpen: boolean;
  setModalOpen: (open) => void;
  isKebabOpen: boolean;
  setKebabOpen: (open) => void;
  kebabItems: ReactElement[];
  deleteModal: () => object;
  deleteKebabIsOpen: boolean;
  setDeleteModalOpen: (open) => void;
  perPage: number;
  page: number;
  setPage: (pageNumber) => void;
  setPerPage: (perPageNumber) => void;
  total: number;
  expandTable: () => void;
  collapseTable: () => void;
};
