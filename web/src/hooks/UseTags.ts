import { useMutation } from "@tanstack/react-query";
import { createTag } from "src/resources/TagResource";

export function useTags(org: string, repo: string){
    const {
      mutate: mutateCreateTag,
      isSuccess: successCreateTag,
      isError: errorCreateTag,
    } = useMutation(
      async ({tag, manifest}: {tag: string; manifest: string}) =>
        createTag(org, repo, tag, manifest),
    );
  
    return {
    createTag: mutateCreateTag,
    successCreateTag: successCreateTag,
    errorCreateTag: errorCreateTag,
    };
}