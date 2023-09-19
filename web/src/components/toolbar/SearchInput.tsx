import {TextInput, ToolbarItem} from '@patternfly/react-core';
import {SetterOrUpdater} from 'recoil';
import {SearchState} from './SearchTypes';

export function SearchInput(props: SearchInput) {
  const setSearchState = (val) => {
    props.onChange((prev: SearchState) => ({...prev, query: val.trim()}));
  };

  return (
    <ToolbarItem>
      <TextInput
        isRequired
        type="search"
        id={props.id ? props.id : 'toolbar-text-input'}
        name="search input"
        placeholder={`Search by ${props.searchState.field}...`}
        value={props.searchState.query}
        onChange={(_event, val) => setSearchState(val)}
      />
    </ToolbarItem>
  );
}

interface SearchInput {
  searchState: SearchState;
  onChange: SetterOrUpdater<SearchState>;
  id?: string;
}
