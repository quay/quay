import OrganizationsList from 'src/routes/OrganizationsList/OrganizationsList';
import Organization from './OrganizationsList/Organization/Organization';
import RepositoryDetails from 'src/routes/RepositoryDetails/RepositoryDetails';
import RepositoriesList from './RepositoriesList/RepositoriesList';
import TagDetails from 'src/routes/TagDetails/TagDetails';
import OverviewList from './OverviewList/OverviewList';

export interface NavigationRoute {
  path: string;
  Component: JSX.Element;
}
const organizationNameBreadcrumb = (match) => {
  return <span>{match.params.organizationName}</span>;
};

const repositoryNameBreadcrumb = (match) => {
  return <span>{match.params.repositoryName}</span>;
};

const tagNameBreadcrumb = (match) => {
  return <span>{match.params.tagName}</span>;
};

const manifestDigestBreadcrumb = (match) => {
  return <span>{match.params.manifestDigest}</span>;
};

const teamMemberBreadcrumb = (match) => {
  return <span>{match.params.teamName}</span>;
};

const Breadcrumb = {
  overviewListBreadcrumb: 'Overview',
  organizationsListBreadcrumb: 'Organization',
  repositoriesListBreadcrumb: 'Repository',
  organizationDetailBreadcrumb: organizationNameBreadcrumb,
  repositoryDetailBreadcrumb: repositoryNameBreadcrumb,
  tagDetailBreadcrumb: tagNameBreadcrumb,
  manifestDigestBreadcrumb: manifestDigestBreadcrumb,
  teamMemberBreadcrumb: teamMemberBreadcrumb,
};

export enum NavigationPath {
  // Side Nav
  home = '/',
  organizationsList = '/organization',

  overviewList = '/overview',

  repositoriesList = '/repository',

  // Organization detail
  organizationDetail = '/organization/:organizationName',

  // Repository detail
  repositoryDetail = '/repository/:organizationName/*',

  // Tag Detail
  tagDetail = '/repository/:organizationName/:repositoryName/tag/:tagName',

  // Manifest Detail
  manifestDetail = '/repository/:organizationName/:repositoryName/manifest/:manifestDigest',

  // Team Member
  teamMember = '/organization/:organizationName/teams/:teamName',

  // Build trigger setup
  setupBuildTrigger = '/repository/:organizationName/:repositoryName/trigger/:triggerUuid',

  // Build info
  buildInfo = '/repository/:organizationName/:repositoryName/build/:buildId',
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

export function getBuildInfoPath(
  currentRoute: string,
  org: string,
  repo: string,
  buildId: string,
) {
  let buildInfoPath = NavigationPath.buildInfo.toString();
  buildInfoPath = buildInfoPath.replace(':organizationName', org);
  buildInfoPath = buildInfoPath.replace(':repositoryName', repo);
  buildInfoPath = buildInfoPath.replace(':buildId', buildId);
  return domainRoute(currentRoute, buildInfoPath);
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
    currentRoute.replace(
      /\/(overview|organization|repository|signin)(?!.*\1).*/,
      '',
    ) + definedRoute
  );
}

export const getNavigationRoutes = () => {
  const currentRoute = window.location.pathname;

  const NavigationRoutes = [
    {
      path: domainRoute(currentRoute, NavigationPath.overviewList),
      element: <OverviewList />,
      breadcrumb: Breadcrumb.overviewListBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.organizationsList),
      element: <OrganizationsList />,
      breadcrumb: Breadcrumb.organizationsListBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.organizationDetail),
      element: <Organization />,
      breadcrumb: Breadcrumb.organizationDetailBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.repositoriesList),
      element: <RepositoriesList organizationName={null} />,
      breadcrumb: Breadcrumb.repositoriesListBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.repositoryDetail),
      element: <RepositoryDetails />,
      breadcrumb: Breadcrumb.repositoryDetailBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.tagDetail),
      element: <TagDetails />,
      breadcrumb: Breadcrumb.tagDetailBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.manifestDetail),
      element: <TagDetails />,
      breadcrumb: Breadcrumb.manifestDigestBreadcrumb,
    },
    {
      path: domainRoute(currentRoute, NavigationPath.teamMember),
      element: <RepositoryDetails />,
      breadcrumb: Breadcrumb.teamMemberBreadcrumb,
    },
  ];
  return NavigationRoutes;
};
