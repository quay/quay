import {atom, selector} from 'recoil';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {OrganizationDetail} from 'src/hooks/UseOrganizations';
import ColumnNames from 'src/routes/OrganizationsList/ColumnNames';
import {OrganizationsTableItem} from 'src/routes/OrganizationsList/OrganizationsList';

export const refreshPageState = atom({
  key: 'refreshOrgPageState',
  default: 0,
});

// Organization List page
export const selectedOrgsState = atom<OrganizationsTableItem[]>({
  key: 'selectedOrgsState',
  default: [],
});

export const searchOrgsState = atom<SearchState>({
  key: 'searchOrgsState',
  default: {
    query: '',
    field: ColumnNames.name,
    isRegEx: false,
  },
});

export const searchOrgsFilterState = selector({
  key: 'searchOrgsFilter',
  get: ({get}) => {
    const search = get(searchOrgsState);
    if (search.query === '') {
      return null;
    }

    const filterByName = (org: OrganizationDetail) =>
      org.name.includes(search.query);
    const filterByNameRegex = (org: OrganizationDetail) => {
      try {
        const regex = new RegExp(search.query, 'i');
        return regex.test(org.name);
      } catch (e) {
        return false;
      }
    };

    if (search.isRegEx) {
      return filterByNameRegex;
    } else {
      return filterByName;
    }
  },
});
