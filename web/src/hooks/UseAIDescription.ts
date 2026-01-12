import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AxiosError} from 'axios';
import {
  AISettings,
  AIError,
  fetchAISettings,
  updateAISettings,
  setAICredentials,
  deleteAICredentials,
  verifyAICredentials,
  generateAIDescription,
  listAIDescriptionTags,
  getCachedDescription,
  UpdateAISettingsRequest,
  SetAICredentialsRequest,
  VerifyAICredentialsRequest,
  GenerateDescriptionRequest,
  GenerateDescriptionResponse,
  VerifyAICredentialsResponse,
  ListAITagsResponse,
} from 'src/resources/AIResource';

/**
 * Hook to fetch AI settings for an organization
 */
export function useAISettings(orgName: string, enabled = true) {
  return useQuery<AISettings, AxiosError>(
    ['aiSettings', orgName],
    () => fetchAISettings(orgName),
    {
      enabled: enabled && !!orgName,
      staleTime: 30000, // 30 seconds
      retry: (failureCount, error) => {
        // Don't retry on 404 (feature not enabled) or 403 (not authorized)
        if (
          error?.response?.status === 404 ||
          error?.response?.status === 403
        ) {
          return false;
        }
        return failureCount < 3;
      },
    },
  );
}

/**
 * Hook to update AI settings
 */
interface UseUpdateAISettingsProps {
  onSuccess?: (data: AISettings) => void;
  onError?: (error: AIError) => void;
}

export function useUpdateAISettings({
  onSuccess,
  onError,
}: UseUpdateAISettingsProps = {}) {
  const queryClient = useQueryClient();

  return useMutation<
    AISettings,
    AxiosError,
    {orgName: string; settings: UpdateAISettingsRequest}
  >(
    async ({orgName, settings}) => {
      return updateAISettings(orgName, settings);
    },
    {
      onSuccess: (data, {orgName}) => {
        queryClient.invalidateQueries(['aiSettings', orgName]);
        onSuccess?.(data);
      },
      onError: (err) => {
        const error = new AIError(
          err.message || 'Failed to update AI settings',
          err.response?.status || 500,
          err,
        );
        onError?.(error);
      },
    },
  );
}

/**
 * Hook to set AI credentials
 */
interface UseSetAICredentialsProps {
  onSuccess?: (data: AISettings) => void;
  onError?: (error: AIError) => void;
}

export function useSetAICredentials({
  onSuccess,
  onError,
}: UseSetAICredentialsProps = {}) {
  const queryClient = useQueryClient();

  return useMutation<
    AISettings,
    AxiosError,
    {orgName: string; credentials: SetAICredentialsRequest}
  >(
    async ({orgName, credentials}) => {
      return setAICredentials(orgName, credentials);
    },
    {
      onSuccess: (data, {orgName}) => {
        queryClient.invalidateQueries(['aiSettings', orgName]);
        onSuccess?.(data);
      },
      onError: (err) => {
        const error = new AIError(
          err.message || 'Failed to set AI credentials',
          err.response?.status || 500,
          err,
        );
        onError?.(error);
      },
    },
  );
}

/**
 * Hook to delete AI credentials
 */
interface UseDeleteAICredentialsProps {
  onSuccess?: () => void;
  onError?: (error: AIError) => void;
}

export function useDeleteAICredentials({
  onSuccess,
  onError,
}: UseDeleteAICredentialsProps = {}) {
  const queryClient = useQueryClient();

  return useMutation<void, AxiosError, string>(
    async (orgName) => {
      return deleteAICredentials(orgName);
    },
    {
      onSuccess: (_, orgName) => {
        queryClient.invalidateQueries(['aiSettings', orgName]);
        onSuccess?.();
      },
      onError: (err) => {
        const error = new AIError(
          err.message || 'Failed to delete AI credentials',
          err.response?.status || 500,
          err,
        );
        onError?.(error);
      },
    },
  );
}

/**
 * Hook to verify AI credentials
 */
interface UseVerifyAICredentialsProps {
  onSuccess?: (data: VerifyAICredentialsResponse) => void;
  onError?: (error: AIError) => void;
}

export function useVerifyAICredentials({
  onSuccess,
  onError,
}: UseVerifyAICredentialsProps = {}) {
  return useMutation<
    VerifyAICredentialsResponse,
    AxiosError,
    {orgName: string; request: VerifyAICredentialsRequest}
  >(
    async ({orgName, request}) => {
      return verifyAICredentials(orgName, request);
    },
    {
      onSuccess: (data) => {
        onSuccess?.(data);
      },
      onError: (err) => {
        const error = new AIError(
          err.message || 'Failed to verify AI credentials',
          err.response?.status || 500,
          err,
        );
        onError?.(error);
      },
    },
  );
}

/**
 * Hook to generate AI description
 */
interface UseGenerateAIDescriptionProps {
  onSuccess?: (data: GenerateDescriptionResponse) => void;
  onError?: (error: AIError) => void;
}

export function useGenerateAIDescription({
  onSuccess,
  onError,
}: UseGenerateAIDescriptionProps = {}) {
  return useMutation<
    GenerateDescriptionResponse,
    AxiosError,
    {namespace: string; repository: string; request: GenerateDescriptionRequest}
  >(
    async ({namespace, repository, request}) => {
      return generateAIDescription(namespace, repository, request);
    },
    {
      onSuccess: (data) => {
        onSuccess?.(data);
      },
      onError: (err) => {
        const error = new AIError(
          err.message || 'Failed to generate description',
          err.response?.status || 500,
          err,
        );
        onError?.(error);
      },
    },
  );
}

/**
 * Hook to list tags for AI description generation
 */
export function useAIDescriptionTags(
  namespace: string,
  repository: string,
  enabled = true,
) {
  return useQuery<ListAITagsResponse, AxiosError>(
    ['aiDescriptionTags', namespace, repository],
    () => listAIDescriptionTags(namespace, repository),
    {
      enabled: enabled && !!namespace && !!repository,
      staleTime: 60000, // 1 minute
    },
  );
}

/**
 * Hook to get cached description
 */
export function useCachedDescription(
  namespace: string,
  repository: string,
  manifestDigest: string | null,
  enabled = true,
) {
  return useQuery(
    ['cachedDescription', namespace, repository, manifestDigest],
    () => getCachedDescription(namespace, repository, manifestDigest as string),
    {
      enabled: enabled && !!namespace && !!repository && !!manifestDigest,
      staleTime: 300000, // 5 minutes
    },
  );
}
