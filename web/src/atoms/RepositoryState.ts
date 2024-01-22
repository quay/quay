import {atom, selector} from 'recoil';
import {OrgSearchState} from 'src/components/toolbar/SearchTypes';
import {RepositoryListColumnNames} from 'src/routes/RepositoriesList/ColumnNames';
import {RepoListTableItem} from 'src/routes/RepositoriesList/RepositoriesList';

export const selectedReposState = atom({
  key: 'selectedReposState',
  default: [],
});

export const searchReposState = atom<OrgSearchState>({
  key: 'searchReposState',
  default: {
    query: '',
    field: RepositoryListColumnNames.name,
    isRegEx: false,
    currentOrganization: null,
  },
});

export const searchReposFilterState = selector({
  key: 'searchReposFilter',
  get: ({get}) => {
    const search = get(searchReposState);
    if (search.query === '') {
      return null;
    }

    const filterByName = (repo: RepoListTableItem) => {
      const repoName =
        search.currentOrganization == null
          ? `${repo.namespace}/${repo.name}`
          : repo.name;
      return repoName.includes(search.query);
    };
    const filterByNameRegex = (repo: RepoListTableItem) => {
      const repoName =
        search.currentOrganization == null
          ? `${repo.namespace}/${repo.name}`
          : repo.name;
      try {
        const regex = new RegExp(search.query, 'i');
        return regex.test(repoName);
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

export const refreshPageState = atom({
  key: 'refreshRepoPageState',
  default: 0,
});

export const selectedReposPermissionState = atom({
  key: 'selectedReposPermissionState',
  default: [],
});
