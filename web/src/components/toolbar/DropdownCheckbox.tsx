import {useState} from 'react';
import {
  Badge,
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleCheckbox,
  MenuToggleElement,
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
      data-testid="select-none-action"
    >
      Select none
    </DropdownItem>,
    <DropdownItem
      key="select-page-items-action"
      component="button"
      onClick={selectPageItems}
      data-testid="select-page-items-action"
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
      data-testid="select-all-items-action"
    >
      Select all ({props.allItemsList?.length})
    </DropdownItem>,
  ];

  const toggleOpen = () => setIsOpen(() => !isOpen);

  return (
    <ToolbarItem variant="bulk-select" onClick={toggleOpen}>
      <Dropdown
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            splitButtonOptions={{
              items: [
                <MenuToggleCheckbox
                  id={props.id ? props.id : 'split-button-text-checkbox'}
                  key="split-checkbox"
                  aria-label="Select all"
                  isChecked={props.selectedItems?.length > 0 ? true : false}
                  onChange={(checked) =>
                    checked ? selectPageItems() : deSelectAll()
                  }
                >
                  {props.selectedItems?.length != 0 ? (
                    <Badge>{props.selectedItems.length}</Badge>
                  ) : null}
                </MenuToggleCheckbox>,
              ],
            }}
            id="toolbar-dropdown-checkbox"
            onChange={toggleOpen}
            onClick={toggleOpen}
          />
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>{dropdownItems}</DropdownList>
      </Dropdown>
    </ToolbarItem>
  );
}

type DropdownCheckboxProps = {
  selectedItems: unknown[];
  deSelectAll: (selectedList) => void;
  allItemsList: unknown[];
  itemsPerPageList: unknown[];
  onItemSelect: (Item, rowIndex, isSelecting) => void;
  id?: string;
};
