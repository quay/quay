import {atom} from 'recoil';
import {IOrganization} from 'src/resources/OrganizationResource';
import ColumnNames from 'src/routes/OrganizationsList/ColumnNames';
import {SearchState} from 'src/components/toolbar/SearchTypes';

export const CurrentUsernameState = atom({
  key: 'currentUsernameState',
  default: '',
});

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
