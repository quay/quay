import {atom} from 'recoil';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {IOrganization} from 'src/resources/OrganizationResource';
import ColumnNames from 'src/routes/OrganizationsList/ColumnNames';

export const refreshPageState = atom({
  key: 'refreshOrgPageState',
  default: 0,
});

// Organization List page
export const selectedOrgsState = atom<IOrganization[]>({
  key: 'selectedOrgsState',
  default: [],
});
export const searchOrgsState = atom<SearchState>({
  key: 'searchOrgsState',
  default: {
    query: '',
    field: ColumnNames.name,
  },
});
