import React from 'react';
import {SearchInput, ToolbarItem} from '@patternfly/react-core';
import {SearchState} from './SearchTypes';
import {SetterOrUpdater} from 'recoil';

export function FilterInput(props: FilterInputProps) {
  const setSearchState = (val: string) => {
    props.onChange((prev: SearchState) => ({...prev, query: val.trim()}));
  };

  return (
    <ToolbarItem variant="search-filter">
      <SearchInput
        placeholder="Search"
        value={props.searchState.query}
        onChange={setSearchState}
        onClear={() => setSearchState('')}
        id={props.id}
      />
    </ToolbarItem>
  );
}

interface FilterInputProps {
  searchState: SearchState;
  onChange: SetterOrUpdater<SearchState>;
  id?: string;
}
