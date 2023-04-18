import {atom} from 'recoil';
import {SearchState} from '../components/toolbar/SearchTypes';

export const selectedTeamsState = atom({
  key: 'selectedTeamsState',
  default: [],
});

export const searchTeamState = atom<SearchState>({
  key: 'searchTeamState',
  default: {
    query: '',
    field: 'name',
  },
});
