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
  const advancedFilterMenuRef = React.useRef<HTMLElement>(null);

  const advancedFilterMenu = (
    <Panel variant="raised" ref={advancedFilterMenuRef}>
      <PanelMain>
        <PanelMainBody>
          <Checkbox
            label="Use regular expressions"
            id="regex-checker"
            name="regex-checkbox"
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

  function validateRegex(value: string): boolean {
    try {
      new RegExp(value);
      return true;
    } catch (e) {
      return false;
    }
  }

  const setSearchState = (
    _event:
      | React.FormEvent<HTMLInputElement>
      | React.SyntheticEvent<HTMLButtonElement>,
    value: string,
  ) => {
    props.onChange((prev: SearchState) => ({
      ...prev,
      query: value.trim(),
      isRegExValid: prev.isRegEx ? validateRegex(value) : true,
    }));
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        advancedFilterMenuRef.current &&
        !advancedFilterMenuRef.current.contains(event.target)
      ) {
        setAdvancedFilterMenuOpen(false);
      }
    };

    // Attach the listeners on Component mount.
    document.addEventListener('mousedown', handleClickOutside);

    // Detach the listeners on Component unmount.
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [advancedFilterMenuRef]);

  const searchInputId = props.id ? props.id : 'toolbar-text-input';

  const widths = {
    default: '150px',
    sm: '130px',
    md: '200px',
    lg: '250px',
    xl: '300px',
    '2xl': '350px',
  };

  return (
    <ToolbarItem variant="search-filter" widths={widths}>
      <SearchInput
        placeholder={`Search by ${props.searchState.field.toLowerCase()}${
          props.searchState.isRegEx ? ' expression' : ''
        }...`}
        value={props.searchState.query}
        onChange={setSearchState}
        onClear={(event) => setSearchState(event, '')}
        id={searchInputId}
        onToggleAdvancedSearch={(e, isOpen) => {
          setAdvancedFilterMenuOpen(isOpen);
        }}
        ref={searchInputRef}
      />
      <Popper
        triggerRef={searchInputRef}
        popper={advancedFilterMenu}
        popperRef={advancedFilterMenuRef}
        isVisible={isAdvancedFilterMenuOpen}
        appendTo={() => document.querySelector(`#${searchInputId}`)}
        enableFlip={false}
      />
    </ToolbarItem>
  );
}

interface FilterInputProps {
  searchState: SearchState;
  onChange: SetterOrUpdater<SearchState>;
  id?: string;
}
