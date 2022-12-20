import {useSetRecoilState} from 'recoil';
import {refreshPageState as orgListRefreshPageState} from 'src/atoms/OrganizationListState';
import {refreshPageState as repoListRefreshPageState} from 'src/atoms/RepositoryState';

export function userRefreshOrgList() {
  const setRefreshOrgList = useSetRecoilState(orgListRefreshPageState);
  return () => setRefreshOrgList((index) => index + 1);
}

export function useRefreshRepoList() {
  const setRefreshRepoList = useSetRecoilState(repoListRefreshPageState);
  return () => setRefreshRepoList((index) => index + 1);
}
