import {Toolbar, ToolbarContent} from '@patternfly/react-core';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {IApplicationToken} from 'src/resources/UserResource';

export default function ApplicationTokensToolbar(
  props: ApplicationTokensToolbarProps,
) {
  const handleSearchChange = (searchState) => {
    props.setSearch(searchState);
    props.setPage(1);
  };

  return (
    <Toolbar>
      <ToolbarContent>
        <SearchInput
          id="application-tokens-search"
          searchState={props.search}
          onChange={handleSearchChange}
          allowSpaces={true}
        />
        <ToolbarPagination
          id="application-tokens-pagination"
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
