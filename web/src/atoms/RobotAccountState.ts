import {atom} from 'recoil';
import {SearchState} from '../components/toolbar/SearchTypes';
import {RobotAccountColumnNames} from 'src/routes/RepositoriesList/ColumnNames';

export const selectedRobotAccountsState = atom({
  key: 'selectedRobotAccountsState',
  default: [],
});

export const searchRobotAccountState = atom<SearchState>({
  key: 'searchRobotAccountState',
  default: {
    query: '',
    field: RobotAccountColumnNames.robotAccountName,
  },
});

export const selectedRobotDefaultPermission = atom({
  key: 'selectedRobotDefaultPermission',
  default: '',
});

export const selectedRobotReposState = atom({
  key: 'selectedRobotReposState',
  default: [],
});

export const selectedRobotReposPermissionState = atom({
  key: 'selectedRobotReposPermissionState',
  default: [],
});
