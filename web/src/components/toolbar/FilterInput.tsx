import {
  Checkbox,
  Panel,
  PanelMain,
  PanelMainBody,
  Popper,
  SearchInput,
  ToolbarItem,
} from '@patternfly/react-core';
import React, {useEffect, useState} from 'react';
import {SetterOrUpdater} from 'recoil';
import {SearchState} from './SearchTypes';

export function FilterInput(props: FilterInputProps) {
  const [isAdvancedFilterMenuOpen, setAdvancedFilterMenuOpen] = useState(false);

  const searchInputRef = React.useRef(null);
  const advancedFilterMenuRef = React.useRef(null);
  const containerRef = React.useRef(null);

  const advancedFilterMenu = (
    <Panel
      variant="raised"
      ref={advancedFilterMenuRef}
      id="filter-input-advanced-search"
    >
      <PanelMain>
        <PanelMainBody>
          <Checkbox
            label="Use regular expressions"
            id="filter-input-regex-checker"
            name="filter-input-regex-checkbox"
            isChecked={props.searchState.isRegEx}
            onChange={(e, checked) =>
              props.onChange((prev: SearchState) => ({
                ...prev,
                isRegEx: checked,
              }))
            }
          />
        </PanelMainBody>
      </PanelMain>
    </Panel>
  );

  const setSearchState = (value: string) => {
    props.onChange((prev: SearchState) => ({
      ...prev,
      query: value.trim(),
    }));
  };

  useEffect(() => {
    if (!isAdvancedFilterMenuOpen) {
      return;
    }

    const handleClickOutside = (event) => {
      if (
        advancedFilterMenuRef.current &&
        !advancedFilterMenuRef.current.contains(event.target)
      ) {
        setAdvancedFilterMenuOpen(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [isAdvancedFilterMenuOpen]);

  const searchInputId = props.id ? props.id : 'toolbar-text-input';

  return (
    <ToolbarItem variant="search-filter">
      <div ref={containerRef}>
        <SearchInput
          ref={searchInputRef}
          placeholder={`Search by ${props.searchState.field.toLowerCase()}${
            props.searchState.isRegEx ? ' expression' : ''
          }...`}
          value={props.searchState.query}
          onChange={(_, value) => {
            setSearchState(value);
            setAdvancedFilterMenuOpen(false);
          }}
          onClear={(_) => setSearchState('')}
          id={searchInputId}
          onToggleAdvancedSearch={() => {
            setAdvancedFilterMenuOpen(!isAdvancedFilterMenuOpen);
          }}
          openMenuButtonAriaLabel="Open advanced search"
          resetButtonLabel="Reset search"
        />
        {isAdvancedFilterMenuOpen && (
          <Popper
            triggerRef={searchInputRef}
            popper={advancedFilterMenu}
            isVisible={isAdvancedFilterMenuOpen}
            appendTo={containerRef.current || undefined}
          />
        )}
      </div>
    </ToolbarItem>
  );
}

interface FilterInputProps {
  searchState: SearchState;
  onChange: SetterOrUpdater<SearchState>;
  id?: string;
}
