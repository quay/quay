import {Toolbar, ToolbarContent, ToolbarItem} from '@patternfly/react-core';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {IApplicationToken} from 'src/resources/UserResource';

export default function ApplicationTokensToolbar(
  props: ApplicationTokensToolbarProps,
) {
  return (
    <Toolbar>
      <ToolbarContent>
        <SearchInput
          id="application-tokens-search"
          searchState={props.search}
          onChange={props.setSearch}
        />
        <ToolbarPagination
          itemsList={props.filteredTokens}
          perPage={props.perPage}
          page={props.page}
          setPage={props.setPage}
          setPerPage={props.setPerPage}
          isCompact={true}
        />
      </ToolbarContent>
    </Toolbar>
  );
}

interface ApplicationTokensToolbarProps {
  filteredTokens: IApplicationToken[];
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  search: SearchState;
  setSearch: (search: SearchState) => void;
}
