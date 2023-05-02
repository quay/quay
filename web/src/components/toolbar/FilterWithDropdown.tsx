import React from 'react';
import {
  TextInput,
  ToolbarItem,
  Dropdown,
  DropdownToggle,
} from '@patternfly/react-core';
import {SearchState} from './SearchTypes';
import {SetterOrUpdater} from 'recoil';

export function FilterWithDropdown(props: FilterWithDropdownProps) {
  const setSearchState = (val: string) => {
    props.onChange((prev: SearchState) => ({...prev, query: val.trim()}));
  };
  const [isOpen, setIsOpen] = React.useState(false);

  const onSelect = () => {
    setIsOpen(false);
  };

  return (
    <ToolbarItem variant="search-filter">
      <Dropdown
        onSelect={onSelect}
        toggle={
          <DropdownToggle
            splitButtonItems={[
              <TextInput
                isRequired
                type="search"
                id="filter-with-dropdown"
                key="filter-with-dropdown"
                name="search input"
                placeholder={props.searchInputText}
                value={props.searchState.query}
                onChange={setSearchState}
              />,
            ]}
            onToggle={(isOpen: boolean) => setIsOpen(isOpen)}
            id="toggle-split-button"
          />
        }
        isOpen={isOpen}
        dropdownItems={props.dropdownItems}
      />
    </ToolbarItem>
  );
}

interface FilterWithDropdownProps {
  searchState: SearchState;
  onChange: SetterOrUpdater<SearchState>;
  dropdownItems: any[];
  searchInputText: string;
}
