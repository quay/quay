import {BulkOperationError, ResourceError} from 'src/resources/ErrorHandling';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  bulkSetExpiration,
  createTag,
  permanentlyDeleteTag,
  bulkDeleteTags,
  getTagPullStatistics,
} from 'src/resources/TagResource';
import {getTags, restoreTag} from 'src/resources/TagResource';

export function useAllTags(org: string, repo: string) {
  // TODO: Returns the first 50 tags due to performance concerns.
  // Need to fetch pages on demand after API redesign.
  const {
    data: tagsResponse,
    isLoading: loadingTags,
    isError: errorLoadingTags,
    error: errorTagsDetails,
    dataUpdatedAt,
  } = useQuery(['namespace', org, 'repo', repo, 'alltags'], () =>
    getTags(org, repo, 1, 50, null, false),
  );

  const tags = tagsResponse?.tags || [];

  return {
    tags: tags,
    loadingTags: loadingTags,
    errorLoadingTags: errorLoadingTags,
    errorTagsDetails: errorTagsDetails,
    lastUpdated: dataUpdatedAt,
  };
}

export function useCreateTag(org: string, repo: string) {
  const {
    mutate: mutateCreateTag,
    isSuccess: successCreateTag,
    isError: errorCreateTag,
  } = useMutation(async ({tag, manifest}: {tag: string; manifest: string}) =>
    createTag(org, repo, tag, manifest),
  );

  return {
    createTag: mutateCreateTag,
    successCreateTag: successCreateTag,
    errorCreateTag: errorCreateTag,
  };
}

export function useSetExpiration(org: string, repo: string) {
  const {
    mutate: mutateSetExpiration,
    isSuccess: successSetExpiration,
    isError: errorSetExpiration,
    error: errorSetExpirationDetails,
  } = useMutation(
    async ({tags, expiration}: {tags: string[]; expiration: number}) =>
      bulkSetExpiration(org, repo, tags, expiration),
  );

  return {
    setExpiration: mutateSetExpiration,
    successSetExpiration: successSetExpiration,
    errorSetExpiration: errorSetExpiration,
    errorSetExpirationDetails:
      errorSetExpirationDetails as BulkOperationError<ResourceError>,
  };
}

export function useDeleteTag(org: string, repo: string) {
  const {
    mutate: mutateDeleteTag,
    isSuccess: successDeleteTags,
    isError: errorDeleteTags,
    error: errorDeleteTagDetails,
  } = useMutation(
    async ({tags, force}: {tags: string[]; force: boolean}) =>
      bulkDeleteTags(org, repo, tags, force),
    {},
  );

  return {
    deleteTags: mutateDeleteTag,
    successDeleteTags: successDeleteTags,
    errorDeleteTags: errorDeleteTags,
    errorDeleteTagDetails:
      errorDeleteTagDetails as BulkOperationError<ResourceError>,
  };
}

export function useRestoreTag(org: string, repo: string) {
  const queryClient = useQueryClient();
  const {mutate, isError, isSuccess} = useMutation(
    async ({tag, digest}: {tag: string; digest: string}) =>
      restoreTag(org, repo, tag, digest),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          org,
          'repo',
          repo,
          'alltags',
        ]);
      },
    },
  );

  return {
    restoreTag: mutate,
    success: isSuccess,
    error: isError,
  };
}

export function usePermanentlyDeleteTag(org: string, repo: string) {
  const queryClient = useQueryClient();
  const {mutate, isError, isSuccess} = useMutation(
    async ({tag, digest}: {tag: string; digest: string}) =>
      permanentlyDeleteTag(org, repo, tag, digest),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          org,
          'repo',
          repo,
          'alltags',
        ]);
      },
    },
  );

  return {
    permanentlyDeleteTag: mutate,
    success: isSuccess,
    error: isError,
  };
}

export function useTagPullStatistics(
  org: string,
  repo: string,
  tag: string,
  enabled = true,
) {
  const {data, isLoading, isError, error} = useQuery(
    ['tagPullStatistics', org, repo, tag],
    () => getTagPullStatistics(org, repo, tag),
    {
      enabled: enabled,
      retry: false,
      staleTime: 60000, // Consider data fresh for 60 seconds
    },
  );

  // Check if this is a 404 (no data available) vs a real error
  const is404 =
    isError &&
    error instanceof ResourceError &&
    (error as ResourceError & {error?: {response?: {status?: number}}}).error
      ?.response?.status === 404;

  // For 404 (no data), return default values with 0 pulls
  // For other errors, return null so components can show error state
  const pullStatistics = is404
    ? {
        tag_name: tag,
        tag_pull_count: 0,
        last_tag_pull_date: null,
        current_manifest_digest: '',
        last_manifest_pull_date: null,
      }
    : data || null;

  return {
    pullStatistics: pullStatistics,
    isLoading: isLoading,
    isError: isError && !is404, // Only report error for non-404 errors
    error: error,
  };
}
