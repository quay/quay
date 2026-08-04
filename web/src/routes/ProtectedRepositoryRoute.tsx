import {lazy, Suspense} from 'react';
import {useLocation} from 'react-router-dom';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useRepository} from 'src/hooks/UseRepository';
import {LoadingPage} from 'src/components/LoadingPage';
import RequestError from 'src/components/errors/RequestError';
import {parseOrgNameFromUrl, parseRepoNameFromUrl} from 'src/libs/utils';

const RepositoryTagRouter = lazy(() => import('./RepositoryTagRouter'));

/**
 * Protected route wrapper for repository pages.
 *
 * For authenticated users: Renders immediately
 * For anonymous users: Pre-checks repo accessibility before rendering
 *
 * This prevents FOUC (Flash of Unauthenticated Content) by ensuring
 * anonymous users NEVER see the layout for private repos.
 */
export default function ProtectedRepositoryRoute(): JSX.Element | null {
  const {user, loading: userLoading} = useCurrentUser();
  const location = useLocation();

  const organization = parseOrgNameFromUrl(location.pathname);
  const repository = parseRepoNameFromUrl(location.pathname);

  const shouldFetchRepo = !userLoading && user?.anonymous;
  const {repoDetails, isLoading, isError, errorLoadingRepoDetails} =
    useRepository(organization, repository, shouldFetchRepo);

  if (userLoading) {
    return null;
  }

  if (user?.anonymous) {
    if (isLoading) {
      return <LoadingPage />;
    }

    if (isError) {
      const status = (errorLoadingRepoDetails as any)?.response?.status;
      if (status === 401 || status === 403) {
        window.location.href = '/signin';
        return null;
      }
      return <RequestError message="Unable to load repository" />;
    }

    if (!repoDetails) {
      return <RequestError message="Repository not found" />;
    }
  }

  return (
    <Suspense fallback={<LoadingPage />}>
      <RepositoryTagRouter />
    </Suspense>
  );
}
