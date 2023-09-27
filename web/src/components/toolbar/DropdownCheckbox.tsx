import {useState} from 'react';
import {
  Dropdown,
  DropdownToggle,
  DropdownToggleCheckbox,
  DropdownItem,
  ToolbarItem,
} from '@patternfly/react-core';

export function DropdownCheckbox(props: DropdownCheckboxProps) {
  const [isOpen, setIsOpen] = useState(false);

  const deSelectAll = () => {
    props.deSelectAll([]);
    setIsOpen(false);
  };

  const selectPageItems = () => {
    props.deSelectAll([]);
    props.itemsPerPageList?.map((value, index) =>
      props.onItemSelect(value, index, true),
    );
    setIsOpen(false);
  };

  const selectAllItems = () => {
    deSelectAll();
    props.allItemsList?.map((value, index) =>
      props.onItemSelect(value, index, true),
    );
    setIsOpen(false);
  };

  const dropdownItems = [
    <DropdownItem
      key="select-none-action"
      component="button"
      onClick={deSelectAll}
    >
      Select none
    </DropdownItem>,
    <DropdownItem
      key="select-page-items-action"
      component="button"
      onClick={selectPageItems}
    >
      Select page (
      {props.allItemsList?.length > props.itemsPerPageList?.length
        ? props.itemsPerPageList?.length
        : props.allItemsList?.length}
      )
    </DropdownItem>,
    <DropdownItem
      key="select-all-items-action"
      component="button"
      onClick={selectAllItems}
    >
      Select all ({props.allItemsList?.length})
    </DropdownItem>,
  ];

  return (
    <ToolbarItem variant="bulk-select">
      <Dropdown
        toggle={
          <DropdownToggle
            splitButtonItems={[
              <DropdownToggleCheckbox
                id={props.id ? props.id : 'split-button-text-checkbox'}
                key="split-checkbox"
                aria-label="Select all"
                isChecked={props.selectedItems?.length > 0 ? true : false}
                onChange={(checked) =>
                  checked ? selectPageItems() : deSelectAll()
                }
              >
                {props.selectedItems?.length != 0
                  ? props.selectedItems?.length + ' selected'
                  : ''}
              </DropdownToggleCheckbox>,
            ]}
            id="toolbar-dropdown-checkbox"
            onToggle={() => setIsOpen(!isOpen)}
          />
        }
        isOpen={isOpen}
        dropdownItems={dropdownItems}
      />
    </ToolbarItem>
  );
}

type DropdownCheckboxProps = {
  selectedItems: any[];
  deSelectAll: (selectedList) => void;
  allItemsList: any[];
  itemsPerPageList: any[];
  onItemSelect: (Item, rowIndex, isSelecting) => void;
  id?: string;
};
