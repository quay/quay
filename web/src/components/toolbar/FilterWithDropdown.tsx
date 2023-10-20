import React from 'react';
import {SetterOrUpdater} from 'recoil';
import {
  Button,
  Dropdown,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
  ToolbarItem,
} from '@patternfly/react-core';
import TimesIcon from '@patternfly/react-icons/dist/esm/icons/times-icon';
import {SearchState} from './SearchTypes';

export function FilterWithDropdown(props: FilterWithDropdownProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  const setSearchState = React.useCallback(
    (val: string) =>
      props.onChange((prev: SearchState) => ({...prev, query: val.trim()})),
    [],
  );

  return (
    <ToolbarItem variant="search-filter">
      <Dropdown
        onSelect={() => setIsOpen(false)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            variant="typeahead"
            isFullWidth
            onClick={() => setIsOpen(() => !isOpen)}
            id="toggle-split-button"
            isExpanded={isOpen}
          >
            <TextInputGroup isPlain>
              <TextInputGroupMain
                id="filter-with-dropdown"
                name="search input"
                placeholder={props.searchInputText}
                value={props.searchState.query}
                onChange={(_event, val: string) => setSearchState(val)}
                autoComplete="off"
              />
            </TextInputGroup>

            <TextInputGroupUtilities>
              {!!props.searchState.query && (
                <Button
                  variant="plain"
                  onClick={() => setSearchState('')}
                  aria-label="Clear input value"
                >
                  <TimesIcon aria-hidden />
                </Button>
              )}
            </TextInputGroupUtilities>
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>{props.dropdownItems}</DropdownList>
      </Dropdown>
    </ToolbarItem>
  );
}

interface FilterWithDropdownProps {
  searchState: SearchState;
  onChange: SetterOrUpdater<SearchState>;
  dropdownItems: any[];
  searchInputText: string;
}
