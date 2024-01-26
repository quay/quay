import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  FileDropResponse,
  SourceRef,
  fetchBuilds,
  fileDrop,
  startBuild,
  startDockerfileBuild,
  uploadFile,
} from 'src/resources/BuildResource';

export function useBuilds(
  org: string,
  repo: string,
  buildsSinceInSeconds: number = null,
) {
  const {data, isError, error, isLoading} = useQuery(
    ['repobuilds', org, repo, String(buildsSinceInSeconds)],
    () => {
      // Keeping the same calls as the old UI for now, if a filter is given fetch 100 builds
      // This can be changed after pagination has been implemented in the API
      return isNullOrUndefined(buildsSinceInSeconds)
        ? fetchBuilds(org, repo, buildsSinceInSeconds)
        : fetchBuilds(org, repo, buildsSinceInSeconds, 100);
    },
  );

  return {
    builds: data,
    isError: isError,
    error: error,
    isLoading: isLoading,
  };
}

export function useStartBuild(
  org: string,
  repo: string,
  triggerUuid: string,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();
  const {mutate} = useMutation(
    async (ref: string | SourceRef) => startBuild(org, repo, triggerUuid, ref),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['repobuilds', org, repo]);
        onSuccess(data);
      },
      onError: onError,
    },
  );

  return {
    startBuild: mutate,
  };
}

export function useStartDockerfileBuild(
  org: string,
  repo: string,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();
  const {mutate} = useMutation(
    async ({
      dockerfileContent,
      robot,
    }: {
      dockerfileContent: string;
      robot: string;
    }) => {
      const fileDropData: FileDropResponse = await fileDrop();
      await uploadFile(fileDropData.url, dockerfileContent);
      return await startDockerfileBuild(org, repo, fileDropData.file_id, robot);
    },
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['repobuilds', org, repo]);
        onSuccess(data);
      },
      onError: onError,
    },
  );

  return {
    startBuild: mutate,
  };
}
