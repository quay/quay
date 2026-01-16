import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  createOrgMirrorConfig,
  deleteOrgMirrorConfig,
  fetchDiscoveredRepositories,
  fetchOrgMirrorConfig,
  OrgMirrorConfig,
  OrgMirrorConfigResponse,
  triggerOrgMirrorSync,
  updateOrgMirrorConfig,
} from 'src/resources/OrgMirrorResource';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {AxiosError} from 'axios';

const ORG_MIRROR_QUERY_KEY = 'orgMirrorConfig';
const DISCOVERED_REPOS_QUERY_KEY = 'orgMirrorDiscoveredRepos';

export function useFetchOrgMirrorConfig(orgName: string, enabled = true) {
  const {
    data: mirrorConfig,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<OrgMirrorConfigResponse | null>(
    [ORG_MIRROR_QUERY_KEY, orgName],
    async ({signal}) => {
      try {
        return await fetchOrgMirrorConfig(orgName, signal);
      } catch (err) {
        // Return null for 404 (no config exists)
        if ((err as AxiosError)?.response?.status === 404) {
          return null;
        }
        throw err;
      }
    },
    {
      enabled: enabled && !!orgName,
      retry: (failureCount, error) => {
        // Don't retry on 404
        if ((error as AxiosError)?.response?.status === 404) {
          return false;
        }
        return failureCount < 3;
      },
    },
  );

  return {
    mirrorConfig,
    isLoading,
    isError,
    error,
    refetch,
  };
}

export function useCreateOrgMirrorConfig(
  orgName: string,
  {
    onSuccess,
    onError,
  }: {
    onSuccess?: () => void;
    onError?: (error: string) => void;
  },
) {
  const queryClient = useQueryClient();

  const {mutate: createMirrorConfig, isLoading: isCreating} = useMutation(
    async (config: OrgMirrorConfig) => {
      return createOrgMirrorConfig(orgName, config);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries([ORG_MIRROR_QUERY_KEY, orgName]);
        onSuccess?.();
      },
      onError: (err: AxiosError) => {
        onError?.(addDisplayError('Failed to create organization mirror', err));
      },
    },
  );

  return {
    createMirrorConfig,
    isCreating,
  };
}

export function useUpdateOrgMirrorConfig(
  orgName: string,
  {
    onSuccess,
    onError,
  }: {
    onSuccess?: () => void;
    onError?: (error: string) => void;
  },
) {
  const queryClient = useQueryClient();

  const {mutate: updateMirrorConfig, isLoading: isUpdating} = useMutation(
    async (config: Partial<OrgMirrorConfig>) => {
      return updateOrgMirrorConfig(orgName, config);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries([ORG_MIRROR_QUERY_KEY, orgName]);
        onSuccess?.();
      },
      onError: (err: AxiosError) => {
        onError?.(addDisplayError('Failed to update organization mirror', err));
      },
    },
  );

  return {
    updateMirrorConfig,
    isUpdating,
  };
}

export function useDeleteOrgMirrorConfig(
  orgName: string,
  {
    onSuccess,
    onError,
  }: {
    onSuccess?: () => void;
    onError?: (error: string) => void;
  },
) {
  const queryClient = useQueryClient();

  const {mutate: deleteMirrorConfig, isLoading: isDeleting} = useMutation(
    async () => {
      return deleteOrgMirrorConfig(orgName);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries([ORG_MIRROR_QUERY_KEY, orgName]);
        onSuccess?.();
      },
      onError: (err: AxiosError) => {
        onError?.(addDisplayError('Failed to delete organization mirror', err));
      },
    },
  );

  return {
    deleteMirrorConfig,
    isDeleting,
  };
}

export function useTriggerOrgMirrorSync(
  orgName: string,
  {
    onSuccess,
    onError,
  }: {
    onSuccess?: () => void;
    onError?: (error: string) => void;
  },
) {
  const queryClient = useQueryClient();

  const {mutate: triggerSync, isLoading: isSyncing} = useMutation(
    async () => {
      return triggerOrgMirrorSync(orgName);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries([ORG_MIRROR_QUERY_KEY, orgName]);
        onSuccess?.();
      },
      onError: (err: AxiosError) => {
        onError?.(addDisplayError('Failed to trigger sync', err));
      },
    },
  );

  return {
    triggerSync,
    isSyncing,
  };
}

export function useFetchDiscoveredRepositories(
  orgName: string,
  status?: string,
  enabled = true,
) {
  const {
    data: discoveredRepos,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery(
    [DISCOVERED_REPOS_QUERY_KEY, orgName, status],
    async ({signal}) => {
      const response = await fetchDiscoveredRepositories(
        orgName,
        status,
        signal,
      );
      return response.repositories;
    },
    {
      enabled: enabled && !!orgName,
    },
  );

  return {
    discoveredRepos: discoveredRepos || [],
    isLoading,
    isError,
    error,
    refetch,
  };
}
