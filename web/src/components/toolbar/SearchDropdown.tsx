import {useState} from 'react';
import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
  ToolbarItem,
} from '@patternfly/react-core';
import {SetterOrUpdater} from 'recoil';
import {SearchState} from './SearchTypes';
import {FilterIcon} from '@patternfly/react-icons';

export function SearchDropdown(props: SearchDropdownProps) {
  if (props.items.length === 0) {
    console.error(
      'No dropdown items given to SearchDropdown. SearchDropdown expects non-empty list.',
    );
  }
  const [isOpen, setIsOpen] = useState(false);

  const onSelect = () => {
    setIsOpen(false);
    const element = document.getElementById('toolbar-dropdown-filter');
    element.focus();
  };

  const onItemSelect = (item) => {
    props.setSearchState((prev: SearchState) => ({...prev, field: item}));
  };

  return (
    <ToolbarItem spacer={{default: 'spacerNone'}}>
      <Dropdown
        onSelect={onSelect}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            icon={<FilterIcon />}
            ref={toggleRef}
            id="toolbar-dropdown-filter"
            onClick={() => setIsOpen(!isOpen)}
            isExpanded={isOpen}
          >
            {props.searchState.field}
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>
          {props.items.map((item: string) => (
            <DropdownItem key={item} onClick={() => onItemSelect(item)}>
              {item}
            </DropdownItem>
          ))}
        </DropdownList>
      </Dropdown>
    </ToolbarItem>
  );
}

interface SearchDropdownProps {
  items: string[];
  searchState: SearchState;
  setSearchState: SetterOrUpdater<SearchState>;
}
