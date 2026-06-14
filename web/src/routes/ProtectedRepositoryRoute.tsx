import {lazy, Suspense} from 'react';
import {useLocation} from 'react-router-dom';
import {Page} from '@patternfly/react-core';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useRepository} from 'src/hooks/UseRepository';
import {QuayHeader} from 'src/components/header/QuayHeader';
import {QuaySidebar} from 'src/components/sidebar/QuaySidebar';
import {parseOrgNameFromUrl, parseRepoNameFromUrl} from 'src/libs/utils';

const RepositoryTagRouter = lazy(() => import('./RepositoryTagRouter'));

/**
 * Protected route wrapper for repository pages.
 *
 * For authenticated users: Renders immediately with full layout
 * For anonymous users: Pre-checks repo accessibility before rendering layout
 *
 * This prevents FOUC (Flash of Unauthenticated Content) by ensuring
 * anonymous users NEVER see the header/sidebar/layout for private repos.
 */
export default function ProtectedRepositoryRoute(): JSX.Element | null {
  const {user, loading: userLoading} = useCurrentUser();
  const location = useLocation();

  const organization = parseOrgNameFromUrl(location.pathname);
  const repository = parseRepoNameFromUrl(location.pathname);

  const shouldFetchRepo = !userLoading && user?.anonymous;
  const {repoDetails} = useRepository(
    organization,
    repository,
    shouldFetchRepo,
  );

  if (userLoading) {
    return null;
  }

  if (user?.anonymous && !repoDetails) {
    return null;
  }

  return (
    <Page
      masthead={<QuayHeader />}
      sidebar={<QuaySidebar />}
      isManagedSidebar
      defaultManagedSidebarIsOpen={true}
      isContentFilled
    >
      <Suspense fallback={null}>
        <RepositoryTagRouter />
      </Suspense>
    </Page>
  );
}
