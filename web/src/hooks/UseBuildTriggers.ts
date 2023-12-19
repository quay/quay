import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  deleteBuildTrigger,
  fetchBuildTriggers,
  toggleBuildTrigger,
} from 'src/resources/BuildResource';

export function useBuildTriggers(org: string, repo: string) {
  const {data, isError, error, isLoading} = useQuery(
    ['repobuildtriggers', org, repo],
    ({signal}) => fetchBuildTriggers(org, repo, signal),
  );

  return {
    triggers: data,
    isError: isError,
    error: error,
    isLoading: isLoading,
  };
}

export function useToggleBuildTrigger(
  namespace: string,
  repo: string,
  trigger_uuid: string,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();
  const {mutate} = useMutation(
    async (enable: boolean) =>
      toggleBuildTrigger(namespace, repo, trigger_uuid, enable),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['repobuildtriggers', namespace, repo]);
        onSuccess();
      },
      onError: onError,
    },
  );

  return {toggleTrigger: mutate};
}

export function useDeleteBuildTrigger(
  namespace: string,
  repo: string,
  trigger_uuid: string,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();
  const {mutate} = useMutation(
    async () => deleteBuildTrigger(namespace, repo, trigger_uuid),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['repobuildtriggers', namespace, repo]);
        onSuccess();
      },
      onError: onError,
    },
  );

  return {deleteTrigger: mutate};
}
