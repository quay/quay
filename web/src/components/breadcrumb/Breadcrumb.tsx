import {
  Breadcrumb,
  BreadcrumbItem,
  PageBreadcrumb,
} from '@patternfly/react-core';
import {getNavigationRoutes, NavigationPath} from 'src/routes/NavigationPath';
import {Link, useParams, useLocation} from 'react-router-dom';
import React, {useEffect, useState} from 'react';
import useBreadcrumbs, {
  BreadcrumbComponentType,
} from 'use-react-router-breadcrumbs';
import {
  parseOrgNameFromUrl,
  parseRepoNameFromUrl,
  parseTagNameFromUrl,
  parseTeamNameFromUrl,
  titleCase,
} from 'src/libs/utils';

export function QuayBreadcrumb() {
  const location = useLocation();

  const [breadcrumbItems, setBreadcrumbItems] = useState<QuayBreadcrumbItem[]>(
    [],
  );
  const routerBreadcrumbs: BreadcrumbData[] = useBreadcrumbs(
    getNavigationRoutes(),
    {
      disableDefaults: true,
      excludePaths: ['/'],
    },
  );
  const urlParams = useParams();

  const resetBreadCrumbs = () => {
    setBreadcrumbItems([]);
  };

  const lastOccurrenceOfSubstring = (substring: string): string => {
    const lastIndex = location.pathname.lastIndexOf(substring);
    return location.pathname.slice(0, lastIndex);
  };

  const fetchBreadcrumb = (
    existingBreadcrumbs,
    nextBreadcrumb,
    routerBreadcrumb,
  ) => {
    // existingBreadcrumbs is a list of breadcrumbs on the page
    // first breadcrumb is either organization or repository
    if (existingBreadcrumbs.length == 0) {
      nextBreadcrumb['title'] = titleCase(
        nextBreadcrumb['pathname'].split('/').at(-1),
      );
    }
    // second breadcrumb is organization name
    else if (existingBreadcrumbs.length == 1) {
      nextBreadcrumb['title'] = parseOrgNameFromUrl(location.pathname);
      nextBreadcrumb['pathname'] =
        location.pathname.split(/repository|organization/)[0] +
        'organization/' +
        nextBreadcrumb['title'];
    }
    // third breadcrumb is repo name or team name
    //  Eg: /organization/<orgname>/<reponame> or /organization/<orgname>/teams/quay?tab=Teamsandmembership
    else if (existingBreadcrumbs.length == 2) {
      switch (routerBreadcrumb.match.route.path) {
        case NavigationPath.repositoryDetail:
          nextBreadcrumb['title'] = parseRepoNameFromUrl(location.pathname);
          nextBreadcrumb['pathname'] =
            lastOccurrenceOfSubstring(nextBreadcrumb['title']) +
            nextBreadcrumb['title'];
          break;
        case NavigationPath.teamMember:
          nextBreadcrumb['title'] = parseTeamNameFromUrl(location.pathname);
          nextBreadcrumb['pathname'] =
            lastOccurrenceOfSubstring(nextBreadcrumb['title']) +
            nextBreadcrumb['title'];
          break;
      }
    }
    // fourth breadcrumb is tag name
    else if (existingBreadcrumbs.length == 3) {
      nextBreadcrumb['title'] = parseTagNameFromUrl(location.pathname);
      nextBreadcrumb['pathname'] =
        existingBreadcrumbs[2]['pathname'] + '/tag/' + nextBreadcrumb['title'];
    }
    if (
      location.pathname.replace(/.*\/organization|.*\/repository/g, '') ==
      nextBreadcrumb['pathname'].replace(/.*\/organization|.*\/repository/g, '')
    ) {
      nextBreadcrumb['active'] = true;
    }
    return nextBreadcrumb;
  };

  const buildFromRoute = () => {
    const result = [];
    for (let i = 0; i < routerBreadcrumbs.length; i++) {
      if (result.length == 4) {
        break;
      }
      let newObj = {};
      const object = routerBreadcrumbs[i];

      newObj['pathname'] = object.match.pathname;
      if (object.key != '') {
        newObj['title'] = object.key.replace(/\//, '');
      }
      newObj = fetchBreadcrumb(result, newObj, object);
      result.push(newObj);
      if (newObj['active']) {
        break;
      }
    }

    setBreadcrumbItems(result);
  };

  useEffect(() => {
    // urlParams has at least one item - Eg: root of the page => {*: 'organization'/'repository'}
    // If size = 1, no params are defined in the url and therefore no breadcrumbs exist for the page. So, we set breadcrumb items as an empty list
    if (Object.keys(urlParams).length <= 1) {
      resetBreadCrumbs();
      return;
    }
    buildFromRoute();
  }, [window.location.pathname]);

  return (
    <div>
      {breadcrumbItems.length > 0 ? (
        <PageBreadcrumb>
          <Breadcrumb test-id="page-breadcrumbs-list">
            {breadcrumbItems.map((object, i) => (
              <BreadcrumbItem
                render={(props) => (
                  <Link
                    to={object.pathname}
                    className={object.active ? 'disabled-link' : ''}
                  >
                    {object.title}
                  </Link>
                )}
                key={i}
              />
            ))}
          </Breadcrumb>
        </PageBreadcrumb>
      ) : (
        ''
      )}
    </div>
  );
}

type QuayBreadcrumbItem = {
  pathname: string;
  title: string;
  active: boolean;
};

declare type Location = ReturnType<typeof useLocation>;

type BreadcrumbData = {
  match: BreadcrumbMatch;
  location: Location;
  key: string;
  breadcrumb: RouterBreadcrumbDetail | React.ReactElement | any;
};

type BreadcrumbMatch = {
  pathname: string;
  route?: BreadcrumbsRoute;
};

type BreadcrumbsRoute = {
  breadcrumb?: BreadcrumbComponentType | any | null;
  Component?: React.ReactElement | any;
};

type RouterBreadcrumbDetail = {
  props: RouterBreadcrumbPropsDetail;
};

type RouterBreadcrumbPropsDetail = {
  children: string;
};
