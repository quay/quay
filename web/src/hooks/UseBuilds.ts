import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useEffect, useState} from 'react';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  FileDropResponse,
  SourceRef,
  cancelBuild,
  fetchBuild,
  fetchBuildLogs,
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

export function useBuild(
  org: string,
  repo: string,
  buildId: string,
  refetchInterval: number = null,
) {
  const {data, isError, error, isLoading} = useQuery(
    ['repobuild', org, repo, buildId],
    () => fetchBuild(org, repo, buildId),
    {
      refetchInterval: refetchInterval,
    },
  );

  return {
    build: data,
    isError,
    error,
    isLoading,
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

export function useCancelBuild(
  org: string,
  repo: string,
  buildId: string,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();
  const {mutate} = useMutation(async () => cancelBuild(org, repo, buildId), {
    onSuccess: (data) => {
      queryClient.invalidateQueries(['repobuilds', org, repo]);
      onSuccess(data);
    },
    onError: onError,
  });

  return {
    cancelBuild: mutate,
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

export interface BuildLogData {
  base_error: string;
  base_image: string;
}

export interface BuildLogEntry {
  type: string;
  logs: any[];
  index: number;
  message: string;
  data: BuildLogData;
}

export function useBuildLogs(
  org: string,
  repo: string,
  buildId: string,
  refetchInterval: number = null,
) {
  const [logEntries, setLogEntries] = useState<BuildLogEntry[]>([]);
  const [logsStartIndex, setLogsStartIndex] = useState(0);
  const {data, isError, error, isLoading, dataUpdatedAt} = useQuery(
    ['repobuildlogs', org, repo, buildId],
    () => fetchBuildLogs(org, repo, buildId, logsStartIndex),
    {refetchInterval: refetchInterval},
  );

  useEffect(() => {
    if (!isNullOrUndefined(data)) {
      const startIndex = data.start;
      const endIndex = data.total;
      let logs = data.logs;

      // If the start index given is less than that requested, then we've received a larger
      // pool of logs, and we need to only consider the new ones.
      if (startIndex < logsStartIndex) {
        logs = logs.slice(logsStartIndex - startIndex);
      }

      const entries = [];
      let parentEntry = null;
      for (let i = 0; i < logs.length; ++i) {
        const entry = logs[i];
        const type = entry['type'] || 'entry';

        // If the type is a command, phase, or error, then it's a top level header
        // in the logs view
        if (type == 'command' || type == 'phase' || type == 'error') {
          entry['logs'] = [];
          entry['index'] = logsStartIndex + i;
          entries.push(entry);

          // Set the new top level header
          parentEntry = entry;
        } else if (!isNullOrUndefined(parentEntry)) {
          // If type is not a top level header, then it's a sub log that will
          // be appended to the last top level header by reference
          parentEntry['logs'].push(entry);
        }
      }
      setLogEntries((prev) => [...prev, ...entries]);
      setLogsStartIndex(endIndex);
    }
  }, [dataUpdatedAt]);

  return {
    logs: logEntries,
    isError,
    error,
    isLoading,
  };
}
