import { useMutation } from "@tanstack/react-query";
import { BulkOperationError, ResourceError } from "src/resources/ErrorHandling";
import { bulkSetExpiration, createTag } from "src/resources/TagResource";

export function useTags(org: string, repo: string){
    const {
      mutate: mutateCreateTag,
      isSuccess: successCreateTag,
      isError: errorCreateTag,
    } = useMutation(
      async ({tag, manifest}: {tag: string; manifest: string}) =>
        createTag(org, repo, tag, manifest),
    );
  
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
    createTag: mutateCreateTag,
    successCreateTag: successCreateTag,
    errorCreateTag: errorCreateTag,
    setExpiration: mutateSetExpiration,
    successSetExpiration: successSetExpiration,
    errorSetExpiration: errorSetExpiration,
    errorSetExpirationDetails: errorSetExpirationDetails as BulkOperationError<ResourceError>,
    };
}
