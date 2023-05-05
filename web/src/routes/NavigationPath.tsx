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

const teamMemberBreadcrumb = (match) => {
  return <span>{match.params.teamName}</span>;
};

const Breadcrumb = {
  organizationsListBreadcrumb: 'Organization',
  repositoriesListBreadcrumb: 'Repository',
  organizationDetailBreadcrumb: organizationNameBreadcrumb,
  repositoryDetailBreadcrumb: repositoryNameBreadcrumb,
  tagDetailBreadcrumb: tagNameBreadcrumb,
  teamMemberBreadcrumb: teamMemberBreadcrumb,
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

  // Team Member
  teamMember = '/organization/:organizationName/teams/:teamName',
}

export function getRepoDetailPath(
  currentRoute: string,
  org: string,
  repo: string,
) {
  // return relative path to repository detail page from repo list table
  let repoPath = NavigationPath.repositoryDetail.toString();
  repoPath = repoPath.replace(':organizationName', org);
  repoPath = repoPath.replace('*', repo);
  return domainRoute(currentRoute, repoPath);
}

export function getTagDetailPath(
  currentRoute: string,
  org: string,
  repo: string,
  tagName: string,
  queryParams: Map<string, string> = null,
) {
  let tagPath = NavigationPath.tagDetail.toString();
  tagPath = tagPath.replace(':organizationName', org);
  tagPath = tagPath.replace(':repositoryName', repo);
  tagPath = tagPath.replace(':tagName', tagName);
  if (queryParams) {
    const params = [];
    for (const entry of Array.from(queryParams.entries())) {
      params.push(entry[0] + '=' + entry[1]);
    }
    tagPath = tagPath + '?' + params.join('&');
  }
  return domainRoute(currentRoute, tagPath);
}

export function getTeamMemberPath(
  currentRoute: string,
  orgName: string,
  teamName: string,
  queryParams: string = null,
): string {
  let teamMemberPath = NavigationPath.teamMember.toString();
  teamMemberPath = teamMemberPath.replace(':organizationName', orgName);
  teamMemberPath = teamMemberPath.replace(':teamName', teamName);
  if (queryParams) {
    teamMemberPath = teamMemberPath + '?tab' + '=' + queryParams;
  }
  return domainRoute(currentRoute, teamMemberPath);
}

export function getDomain() {
  return process.env.REACT_APP_QUAY_DOMAIN || 'quay.io';
}

function domainRoute(currentRoute, definedRoute) {
  /***
   * This function returns prefix + route.
   Eg:If quay is hosted on https://stage.foo.redhat.com:1337/settings/quay/organization,
   window.location.pathname here is `/settings/quay/organization`,
   the regex removes everything after organization and returns /settings/quay.
   So, the function returns /settings/quay/<route> .
   ***/
  return (
    currentRoute.replace(/\/(organization|repository|signin)(?!.*\1).*/, '') +
    definedRoute
  );
}

export const getNavigationRoutes = () => {
  const currentRoute = window.location.pathname;

  const NavigationRoutes = [
    {
      path: domainRoute(currentRoute, NavigationPath.organizationsList),
      Component: <OrganizationsList />,
      breadcrumb: Breadcrumb.organizationsListBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.organizationDetail),
      Component: <Organization />,
      breadcrumb: Breadcrumb.organizationDetailBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.repositoriesList),
      Component: <RepositoriesList organizationName={null} />,
      breadcrumb: Breadcrumb.repositoriesListBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.repositoryDetail),
      Component: <RepositoryDetails />,
      breadcrumb: Breadcrumb.repositoryDetailBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.tagDetail),
      Component: <TagDetails />,
      breadcrumb: Breadcrumb.tagDetailBreadcrumb,
    },
  ];
  return NavigationRoutes;
};
