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

function domainRoute(definedRoute) {
  /***
   * This function returns prefix + route.
   Eg:If quay is hosted on https://stage.foo.redhat.com:1337/settings/quay/organization,
   window.location.pathname here is `/settings/quay/organization`,
   the regex removes everything after organization and returns /settings/quay.
   So, the function returns /settings/quay/<route> .
   ***/
  const currentRoute = window.location.pathname;
  return (
    // This regex replaces everything after the last occurrence of organization|repository|signin with empty string.
    // Doing this gives us the prefix.
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
