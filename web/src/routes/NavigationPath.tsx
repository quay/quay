import OrganizationsList from 'src/routes/OrganizationsList/OrganizationsList';
import Organization from './OrganizationsList/Organization/Organization';
import RepositoryDetails from 'src/routes/RepositoryDetails/RepositoryDetails';
import RepositoriesList from './RepositoriesList/RepositoriesList';
import TagDetails from 'src/routes/TagDetails/TagDetails';

const organizationNameBreadcrumb = (match) => {
  return <span>{match.params.organizationName}</span>;
};

const repositoryNameBreadcrumb = (match) => {
  return <span>{match.params.repositoryName}</span>;
};

const tagNameBreadcrumb = (match) => {
  return <span>{match.params.tagName}</span>;
};

const Breadcrumb = {
  organizationsListBreadcrumb: 'Organization',
  repositoriesListBreadcrumb: 'Repository',
  organizationDetailBreadcrumb: organizationNameBreadcrumb,
  repositoryDetailBreadcrumb: repositoryNameBreadcrumb,
  tagDetailBreadcrumb: tagNameBreadcrumb,
};

export enum NavigationPath {
  // Side Nav
  home = '/',
  organizationsList = '/organization',

  repositoriesList = '/repository',

  // Organization detail
  organizationDetail = '/organization/:organizationName',

  // Repository detail
  repositoryDetail = '/repository/:organizationName/*',

  // Tag Detail
  tagDetail = '/tag/:organizationName/*',
}

export function getRepoDetailPath(org: string, repo: string) {
  let repoPath = NavigationPath.repositoryDetail.toString();
  repoPath = repoPath.replace(':organizationName', org);
  repoPath = repoPath.replace('*', repo);
  return repoPath;
}

export function getTagDetailPath(
  org: string,
  repo: string,
  tag: string,
  queryParams: Map<string, string> = null,
) {
  let tagPath = NavigationPath.tagDetail.toString();
  tagPath = tagPath.replace(':organizationName', org);
  tagPath = tagPath.replace('*', `${repo}/${tag}`);
  if (queryParams) {
    const params = [];
    for (const entry of Array.from(queryParams.entries())) {
      params.push(entry[0] + '=' + entry[1]);
    }
    tagPath = tagPath + '?' + params.join('&');
  }
  return tagPath;
}

export function getDomain() {
  return process.env.REACT_APP_QUAY_DOMAIN || 'quay.io';
}

const NavigationRoutes = [
  {
    path: NavigationPath.organizationsList,
    Component: <OrganizationsList />,
    breadcrumb: Breadcrumb.organizationsListBreadcrumb,
  },
  {
    path: NavigationPath.organizationDetail,
    Component: <Organization />,
    breadcrumb: Breadcrumb.organizationDetailBreadcrumb,
  },
  {
    path: NavigationPath.repositoriesList,
    Component: <RepositoriesList />,
    breadcrumb: Breadcrumb.repositoriesListBreadcrumb,
  },
  {
    path: NavigationPath.repositoryDetail,
    Component: <RepositoryDetails />,
    breadcrumb: Breadcrumb.repositoryDetailBreadcrumb,
  },
  {
    path: NavigationPath.tagDetail,
    Component: <TagDetails />,
    breadcrumb: Breadcrumb.tagDetailBreadcrumb,
  },
];
export {NavigationRoutes};
