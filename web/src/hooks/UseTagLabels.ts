import {useMutation, useQuery} from '@tanstack/react-query';
import {useEffect, useState} from 'react';
import {BulkOperationError, ResourceError} from 'src/resources/ErrorHandling';
import {
  Label,
  bulkCreateLabels,
  bulkDeleteLabels,
  getLabels,
} from 'src/resources/TagResource';

export function useLabels(
  org: string,
  repo: string,
  digest: string,
  cache?: Record<string, Label[]>,
  setCache?: (cache: Record<string, Label[]>) => void,
) {
  const [labels, setLabels] = useState<Label[]>([]);

  // Check cache first
  const cachedLabels = cache?.[digest];
  const shouldFetch = !cachedLabels;

  const {
    data: initialLabels,
    isLoading: loading,
    isError: error,
  } = useQuery(
    ['namespace', org, 'repo', repo, 'digest', digest, 'labels'],
    ({signal}) => getLabels(org, repo, digest, signal),
    {
      enabled: shouldFetch,
      placeholderData: cachedLabels || [],
      onSuccess: (result) => {
        setLabels(result);
        // Update cache on successful fetch
        if (setCache && result) {
          setCache((prev) => ({...prev, [digest]: result}));
        }
      },
    },
  );

  // Use effect to set cached labels without causing infinite render
  useEffect(() => {
    if (cachedLabels) {
      setLabels(cachedLabels);
    }
  }, [digest]); // Only run when digest changes

  const {
    mutate: bulkCreateLabelsMutator,
    isSuccess: successCreateLabels,
    isError: errorCreateLabels,
    error: detailedErrorCreateLabels,
    isLoading: loadingCreateLabels,
  } = useMutation(async (labels: Label[]) => {
    await bulkCreateLabels(org, repo, digest, labels);
  });

  const {
    mutate: bulkDeleteLabelsMutator,
    isSuccess: successDeleteLabels,
    isError: errorDeleteLabels,
    error: detailedErrorDeleteLabels,
    isLoading: loadingDeleteLabels,
  } = useMutation(async (labels: Label[]) => {
    await bulkDeleteLabels(org, repo, digest, labels);
  });

  return {
    labels: labels,
    setLabels: setLabels,
    initialLabels: initialLabels,
    loading: loading,
    error: error,
    createLabels: bulkCreateLabelsMutator,
    successCreatingLabels: successCreateLabels,
    errorCreatingLabels: errorCreateLabels,
    errorCreatingLabelsDetails:
      detailedErrorCreateLabels as BulkOperationError<ResourceError>,
    loadingCreateLabels: loadingCreateLabels,
    deleteLabels: bulkDeleteLabelsMutator,
    successDeletingLabels: successDeleteLabels,
    errorDeletingLabels: errorDeleteLabels,
    errorDeletingLabelsDetails:
      detailedErrorDeleteLabels as BulkOperationError<ResourceError>,
    loadingDeleteLabels: loadingDeleteLabels,
  };
}
