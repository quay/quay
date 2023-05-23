import {
  Breadcrumb,
  BreadcrumbItem,
  PageBreadcrumb,
} from '@patternfly/react-core';
import {getNavigationRoutes} from 'src/routes/NavigationPath';
import {Link, useParams, useLocation} from 'react-router-dom';
import React, {useEffect, useState} from 'react';
import useBreadcrumbs, {
  BreadcrumbComponentType,
} from 'use-react-router-breadcrumbs';
import {useRecoilState} from 'recoil';
import {BrowserHistoryState} from 'src/atoms/BrowserHistoryState';
import {parseOrgNameFromUrl, parseRepoNameFromUrl, parseTagNameFromUrl} from 'src/libs/utils';

export function QuayBreadcrumb() {
  const location = useLocation();
  const [browserHistory, setBrowserHistoryState] =
    useRecoilState(BrowserHistoryState);

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
    setBrowserHistoryState([]);
  };

  const fetchBreadcrumb = (existingBreadcrumbs, nextBreadcrumb) => {
    // if existingBreadcrumbs.len is 0 -> next entry is either organization or repository
    if (existingBreadcrumbs.length == 0) {
      nextBreadcrumb['title'] = nextBreadcrumb['pathname'].split('/').at(-1);
    }
    // if existingBreadcrumbs.len is 1 -> next entry is organization name
    else if (existingBreadcrumbs.length == 1) {
      nextBreadcrumb['title'] = parseOrgNameFromUrl(location.pathname);
      nextBreadcrumb['pathname'] = location.pathname.split(/repository|organization/)[0] + 'organization/' + nextBreadcrumb['title'];
    }
    // if existingBreadcrumbs.len is 2 -> next entry is repo name
    else if (existingBreadcrumbs.length == 2) {
      nextBreadcrumb['title'] = parseRepoNameFromUrl(location.pathname);
      nextBreadcrumb['pathname'] = location.pathname.split(nextBreadcrumb['title'])[0] + nextBreadcrumb['title'];
    }
    // if existingBreadcrumbs.len is 3 -> next entry is tag name
    else if (existingBreadcrumbs.length == 3) {
      nextBreadcrumb['title'] = parseTagNameFromUrl(location.pathname)
      nextBreadcrumb['pathname'] = existingBreadcrumbs[2]['pathname'] + '/tag/' + nextBreadcrumb['title'];
    }
    if (location.pathname.replace(/.*\/organization|.*\/repository/g, '') == nextBreadcrumb['pathname'].replace(/.*\/organization|.*\/repository/g, '')) {
      nextBreadcrumb['active'] = true;
    }
    return nextBreadcrumb;
  }

  const buildFromRoute = () => {
    const result = [];
    const history = [];
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
      newObj = fetchBreadcrumb(result, newObj)
      result.push(newObj);
      history.push(newObj);
      if (newObj['active']) {
        break;
      }
    }

    setBreadcrumbItems(result);
    setBrowserHistoryState(history);
  };

  const currentBreadcrumbItem = () => {
    const newItem = {};
    const lastItem = routerBreadcrumbs[routerBreadcrumbs.length - 1];
    newItem['pathname'] = location.pathname;
    const tagName = parseTagNameFromUrl(newItem['pathname']);
    // Form QuayBreadcrumbItem for the current path
    if (tagName != '') {
      newItem['title'] = parseTagNameFromUrl(newItem['pathname'])
    }
    else if (lastItem.match.route.path.match('/repository/:organizationName/*')) {
      newItem['title'] = parseRepoNameFromUrl(location.pathname);
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
      if (result.length == 3) {
        break;
      }
      let newObj = {};
      newObj['pathname'] = value['pathname'];
      newObj = fetchBreadcrumb(result, newObj);
      if (newObj['active']) {
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
  }, [window.location.pathname]);

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
