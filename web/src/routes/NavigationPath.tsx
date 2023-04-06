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
  tagDetail = '/repository/:organizationName/:repositoryName/tag/:tagName',
}

export function getRepoDetailPath(org: string, repo: string) {
  // return relative path to repository detail page from repo list table
  return `../../repository/${org}/${repo}`;
}

export function getTagDetailPath(
  org: string,
  repo: string,
  tagName: string,
  queryParams: Map<string, string> = null,
) {
  let tagPath = `${repo}/tag/${tagName}`;
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

function domainRoute(definedRoute) {
  const currentRoute = window.location.pathname;
  return (
    currentRoute.replace(/\/(\/organization|repository|signin)(?!.*\1).*/, '') +
    definedRoute
  );
}

const NavigationRoutes = [
  {
    path: domainRoute(NavigationPath.organizationsList),
    Component: <OrganizationsList />,
    breadcrumb: Breadcrumb.organizationsListBreadcrumb,
  },
  {
    path: domainRoute(NavigationPath.organizationDetail),
    Component: <Organization />,
    breadcrumb: Breadcrumb.organizationDetailBreadcrumb,
  },
  {
    path: domainRoute(NavigationPath.repositoriesList),
    Component: <RepositoriesList />,
    breadcrumb: Breadcrumb.repositoriesListBreadcrumb,
  },
  {
    path: domainRoute(NavigationPath.repositoryDetail),
    Component: <RepositoryDetails />,
    breadcrumb: Breadcrumb.repositoryDetailBreadcrumb,
  },
  {
    path: domainRoute(NavigationPath.tagDetail),
    Component: <TagDetails />,
    breadcrumb: Breadcrumb.tagDetailBreadcrumb,
  },
];
export {NavigationRoutes};
