import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  analyzeBuildTrigger,
  deleteBuildTrigger,
  fetchBuildTrigger,
  fetchBuildTriggers,
  toggleBuildTrigger,
  activateBuildTrigger,
  TriggerConfig,
  RepositoryBuildTrigger,
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

export function useFetchBuildTrigger(
  org: string,
  repo: string,
  triggerUuid: string,
) {
  const {data, isError, error, isLoading} = useQuery(
    ['repobuildtrigger', org, repo, triggerUuid],
    ({signal}) => fetchBuildTrigger(org, repo, triggerUuid, signal),
    {enabled: !isNullOrUndefined(triggerUuid)},
  );

  return {
    trigger: data,
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

export function useAnalyzeBuildTrigger(
  namespace: string,
  repo: string,
  triggerUuid: string,
  buildSource: string,
  context: string,
  dockerfilePath: string,
) {
  const {data, isError, error, isLoading, isSuccess} = useQuery(
    ['analyzebuildtrigger', namespace, repo],
    () =>
      analyzeBuildTrigger(
        namespace,
        repo,
        triggerUuid,
        buildSource,
        context,
        dockerfilePath,
      ),
  );

  return {
    analysis: data,
    isError: isError,
    error: error,
    isLoading: isLoading,
    isSuccess,
  };
}

export function useActivateBuildTrigger(
  namespace: string,
  repo: string,
  triggerUuid: string,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();
  const {mutate} = useMutation(
    async ({config, robot}: {config: TriggerConfig; robot: string}) =>
      activateBuildTrigger(namespace, repo, triggerUuid, config, robot),
    {
      onSuccess: (data: RepositoryBuildTrigger) => {
        queryClient.invalidateQueries(['repobuildtriggers', namespace, repo]);
        onSuccess(data);
      },
      onError: onError,
    },
  );

  return {activateTrigger: mutate};
}
