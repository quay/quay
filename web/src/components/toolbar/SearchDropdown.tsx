import {useState} from 'react';
import {
  Dropdown,
  DropdownToggle,
  DropdownItem,
  ToolbarItem,
} from '@patternfly/react-core';
import {SetterOrUpdater} from 'recoil';
import {SearchState} from './SearchTypes';

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

  const dropdownItems = props.items.map((item: string) => (
    <DropdownItem
      key={item}
      onClick={() => {
        onItemSelect(item);
      }}
    >
      {item}
    </DropdownItem>
  ));

  return (
    <ToolbarItem spacer={{default: 'spacerNone'}}>
      <Dropdown
        onSelect={onSelect}
        toggle={
          <DropdownToggle
            id="toolbar-dropdown-filter"
            onToggle={() => setIsOpen(!isOpen)}
          >
            {props.searchState.field}
          </DropdownToggle>
        }
        isOpen={isOpen}
        dropdownItems={dropdownItems}
      />
    </ToolbarItem>
  );
}

interface SearchDropdownProps {
  items: string[];
  searchState: SearchState;
  setSearchState: SetterOrUpdater<SearchState>;
}
