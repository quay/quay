import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  fetchOrganizationQuota,
  createOrganizationQuota,
  updateOrganizationQuota,
  deleteOrganizationQuota,
  createQuotaLimit,
  updateQuotaLimit,
  deleteQuotaLimit,
  IQuota,
  ICreateQuotaParams,
  IUpdateQuotaParams,
  ICreateQuotaLimitParams,
} from 'src/resources/QuotaResource';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {AxiosError} from 'axios';

// Hook to fetch organization quota (or user quota if isUser=true)
export function useFetchOrganizationQuota(orgName: string, isUser?: boolean) {
  const {
    data: organizationQuotas,
    isLoading: isLoadingQuotas,
    isSuccess: isSuccessLoadingQuotas,
    isError: errorLoadingQuotas,
  } = useQuery<IQuota[]>(
    ['organizationquota', orgName, isUser],
    ({signal}) => fetchOrganizationQuota(orgName, signal, isUser),
    {
      enabled: !!orgName,
    },
  );

  // Return the first quota (organization can only have one quota currently)
  const organizationQuota = organizationQuotas?.[0] || null;

  return {
    organizationQuota,
    organizationQuotas,
    isLoadingQuotas,
    errorLoadingQuotas,
    isSuccessLoadingQuotas,
  };
}

// Hook to create organization quota (or user quota if isUser=true)
export function useCreateOrganizationQuota(
  orgName: string,
  {onSuccess, onError},
  isUser?: boolean,
) {
  const queryClient = useQueryClient();

  const {mutate: createQuotaMutation, isLoading: isCreatingQuota} = useMutation(
    async (params: ICreateQuotaParams) => {
      return createOrganizationQuota(orgName, params, isUser);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['organizationquota', orgName, isUser]);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('quota creation error', err));
      },
    },
  );

  return {
    createQuotaMutation,
    isCreatingQuota,
  };
}

// Hook to update organization quota (or user quota if isUser=true)
export function useUpdateOrganizationQuota(
  orgName: string,
  {onSuccess, onError},
  isUser?: boolean,
) {
  const queryClient = useQueryClient();

  const {mutate: updateQuotaMutation, isLoading: isUpdatingQuota} = useMutation(
    async ({
      quotaId,
      params,
    }: {
      quotaId: string;
      params: IUpdateQuotaParams;
    }) => {
      return updateOrganizationQuota(orgName, quotaId, params, isUser);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['organizationquota', orgName, isUser]);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('quota update error', err));
      },
    },
  );

  return {
    updateQuotaMutation,
    isUpdatingQuota,
  };
}

// Hook to delete organization quota (or user quota if isUser=true)
export function useDeleteOrganizationQuota(
  orgName: string,
  {onSuccess, onError},
  isUser?: boolean,
) {
  const queryClient = useQueryClient();

  const {mutate: deleteQuotaMutation, isLoading: isDeletingQuota} = useMutation(
    async (quotaId: string) => {
      return deleteOrganizationQuota(orgName, quotaId, isUser);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['organizationquota', orgName, isUser]);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('quota deletion error', err));
      },
    },
  );

  return {
    deleteQuotaMutation,
    isDeletingQuota,
  };
}

// Hook to create quota limit (for organization or user quota)
export function useCreateQuotaLimit(
  orgName: string,
  {onSuccess, onError},
  isUser?: boolean,
) {
  const queryClient = useQueryClient();

  const {mutate: createLimitMutation, isLoading: isCreatingLimit} = useMutation(
    async ({
      quotaId,
      params,
    }: {
      quotaId: string;
      params: ICreateQuotaLimitParams;
    }) => {
      return createQuotaLimit(orgName, quotaId, params);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['organizationquota', orgName, isUser]);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('quota limit creation error', err));
      },
    },
  );

  return {
    createLimitMutation,
    isCreatingLimit,
  };
}

// Hook to update quota limit (for organization or user quota)
export function useUpdateQuotaLimit(
  orgName: string,
  {onSuccess, onError},
  isUser?: boolean,
) {
  const queryClient = useQueryClient();

  const {mutate: updateLimitMutation, isLoading: isUpdatingLimit} = useMutation(
    async ({
      quotaId,
      limitId,
      params,
    }: {
      quotaId: string;
      limitId: string;
      params: ICreateQuotaLimitParams;
    }) => {
      return updateQuotaLimit(orgName, quotaId, limitId, params);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['organizationquota', orgName, isUser]);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('quota limit update error', err));
      },
    },
  );

  return {
    updateLimitMutation,
    isUpdatingLimit,
  };
}

// Hook to delete quota limit (for organization or user quota)
export function useDeleteQuotaLimit(
  orgName: string,
  {onSuccess, onError},
  isUser?: boolean,
) {
  const queryClient = useQueryClient();

  const {mutate: deleteLimitMutation, isLoading: isDeletingLimit} = useMutation(
    async ({quotaId, limitId}: {quotaId: string; limitId: string}) => {
      return deleteQuotaLimit(orgName, quotaId, limitId);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['organizationquota', orgName, isUser]);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('quota limit deletion error', err));
      },
    },
  );

  return {
    deleteLimitMutation,
    isDeletingLimit,
  };
}
