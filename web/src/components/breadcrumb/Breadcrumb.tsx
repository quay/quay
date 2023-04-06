import {
  Breadcrumb,
  BreadcrumbItem,
  PageBreadcrumb,
} from '@patternfly/react-core';
import {NavigationRoutes} from 'src/routes/NavigationPath';
import {Link, useParams, useLocation} from 'react-router-dom';
import React, {useEffect, useState} from 'react';
import useBreadcrumbs, {
  BreadcrumbComponentType,
} from 'use-react-router-breadcrumbs';
import {useRecoilState} from 'recoil';
import {BrowserHistoryState} from 'src/atoms/BrowserHistoryState';

export function QuayBreadcrumb() {
  const [browserHistory, setBrowserHistoryState] =
    useRecoilState(BrowserHistoryState);

  const [breadcrumbItems, setBreadcrumbItems] = useState<QuayBreadcrumbItem[]>(
    [],
  );
  const routerBreadcrumbs: BreadcrumbData[] = useBreadcrumbs(NavigationRoutes, {
    disableDefaults: true,
    excludePaths: ['/'],
  });
  const urlParams = useParams();

  const resetBreadCrumbs = () => {
    setBreadcrumbItems([]);
    setBrowserHistoryState([]);
  };

  const fetchRepoName = (route) => {
    const re = new RegExp(urlParams.organizationName + '/(.*)', 'i');
    const result = route.match(re);
    return result[1];
  };

  const buildBreadCrumbFromPrevRoute = (object) => {
    const prevObj = {};
    prevObj['pathname'] = object.match.pathname;
    prevObj['title'] = fetchRepoName(prevObj['pathname']);
    prevObj['active'] =
      prevObj['pathname'].localeCompare(window.location.pathname) === 0;
    return prevObj;
  };

  const buildFromRoute = () => {
    const result = [];
    const history = [];
    let prevItem = null;

    for (let i = 0; i < routerBreadcrumbs.length; i++) {
      const newObj = {};
      const object = routerBreadcrumbs[i];
      newObj['pathname'] = object.match.pathname;
      if (object.match.route.Component.type.name == 'RepositoryDetails') {
        prevItem = object;
        // Continuing till we find the last RepositoryDetails route for nested repo paths
        continue;
      } else {
        newObj['title'] = object.match.pathname.split('/').slice(-1)[0];
      }
      newObj['active'] =
        object.match.pathname.localeCompare(window.location.pathname) === 0;

      if (prevItem) {
        const prevObj = buildBreadCrumbFromPrevRoute(prevItem);
        result.push(prevObj);
        history.push(prevObj);
        prevItem = null;
      }

      result.push(newObj);
      history.push(newObj);
    }

    // If prevItem was not pushed in the for loop
    if (prevItem) {
      const prevObj = buildBreadCrumbFromPrevRoute(prevItem);
      result.push(prevObj);
      history.push(prevObj);
      prevItem = null;
    }

    setBreadcrumbItems(result);
    setBrowserHistoryState(history);
  };

  const currentBreadcrumbItem = () => {
    const newItem = {};
    const lastItem = routerBreadcrumbs[routerBreadcrumbs.length - 1];

    newItem['pathname'] = lastItem.location.pathname;
    // Form QuayBreadcrumbItem for the current path
    if (lastItem.match.route.Component.type.name == 'RepositoryDetails') {
      newItem['title'] = fetchRepoName(newItem['pathname']);
    } else {
      newItem['title'] = newItem['pathname'].split('/').slice(-1)[0];
    }

    newItem['active'] = true;
    return newItem;
  };

  const buildFromBrowserHistory = () => {
    const result = [];
    const history = [];
    const newItem = currentBreadcrumbItem();

    for (const value of Array.from(browserHistory.values())) {
      const newObj = {};
      newObj['pathname'] = value['pathname'];
      if (typeof value['title'] === 'string') {
        newObj['title'] = value['title'];
      } else if (value.title?.props?.children) {
        newObj['title'] = value['title']['props']['children'];
      }
      newObj['active'] =
        value['pathname'].localeCompare(window.location.pathname) === 0;
      if (newItem['pathname'] == newObj['pathname']) {
        newItem['title'] = newObj['title'];
        break;
      }
      result.push(newObj);
      history.push(newObj);
    }
    result.push(newItem);
    history.push(newItem);
    setBreadcrumbItems(result);
    setBrowserHistoryState(history);
  };

  useEffect(() => {
    // urlParams has atleast one item - {*: 'endpoint'}
    // If size = 1, no params are defined in the url, so we reset breadcrumb history
    if (Object.keys(urlParams).length <= 1) {
      resetBreadCrumbs();
      return;
    }

    if (browserHistory.length > 0) {
      buildFromBrowserHistory();
    } else {
      buildFromRoute();
    }
  }, []);

  return (
    <div>
      {breadcrumbItems.length > 0 ? (
        <PageBreadcrumb>
          <Breadcrumb>
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
