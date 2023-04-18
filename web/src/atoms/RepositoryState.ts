import {atom} from 'recoil';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {RepositoryListColumnNames} from 'src/routes/RepositoriesList/ColumnNames';

export const selectedReposState = atom({
  key: 'selectedReposState',
  default: [],
});

export const searchRepoState = atom<SearchState>({
  key: 'searchRepoState',
  default: {
    query: '',
    field: RepositoryListColumnNames.name,
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
