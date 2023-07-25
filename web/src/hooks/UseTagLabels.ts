import { useMutation, useQuery } from "@tanstack/react-query";
import { ReactNode, useState } from "react";
import { BulkOperationError, ResourceError } from "src/resources/ErrorHandling";
import { Label, bulkCreateLabels, bulkDeleteLabels, getLabels } from "src/resources/TagResource";

export function useLabels(org: string, repo: string, digest: string) {
    const [labels, setLabels] = useState<Label[]>([]);
    const {
        data: initialLabels,
        isLoading: loading,
        isError: error,
    } = useQuery(
        ['namespace', org, 'repo', repo, 'digest', digest, 'labels'],
        ({ signal }) =>
            getLabels(org, repo, digest, signal),
        {
            enabled: true,
            placeholderData: [],
            onSuccess: (result) => {
                setLabels(result);
            },
        },
    );

    const {
        mutate: bulkCreateLabelsMutator,
        isSuccess: successCreateLabels,
        isError: errorCreateLabels,
        error: detailedErrorCreateLabels,
        isLoading: loadingCreateLabels,
    } = useMutation(
        async (labels: Label[]) => {
            await bulkCreateLabels(org, repo, digest, labels);
        },
    );

    const {
        mutate: bulkDeleteLabelsMutator,
        isSuccess: successDeleteLabels,
        isError: errorDeleteLabels,
        error: detailedErrorDeleteLabels,
        isLoading: loadingDeleteLabels,
    } = useMutation(
        async (labels: Label[]) => {
            await bulkDeleteLabels(org, repo, digest, labels);
        },
    );

    return {
        labels: labels,
        setLabels: setLabels,
        initialLabels: initialLabels,
        loading: loading,
        error: error,
        createLabels: bulkCreateLabelsMutator,
        successCreatingLabels: successCreateLabels,
        errorCreatingLabels: errorCreateLabels,
        errorCreatingLabelsDetails: detailedErrorCreateLabels as BulkOperationError<ResourceError>,
        loadingCreateLabels: loadingCreateLabels,
        deleteLabels: bulkDeleteLabelsMutator,
        successDeletingLabels: successDeleteLabels,
        errorDeletingLabels: errorDeleteLabels,
        errorDeletingLabelsDetails: detailedErrorDeleteLabels as BulkOperationError<ResourceError>,
        loadingDeleteLabels: loadingDeleteLabels,
    }
}
