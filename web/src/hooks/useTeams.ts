import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {createNewTeamForNamespac} from 'src/resources/TeamResources';
import {useState} from 'react';

export function useTeams(ns) {
  const [namespace, setNamespace] = useState(ns);
  const queryClient = useQueryClient();

  const createTeamMutator = useMutation(
    async ({namespace, name, description}: createNewTeamForNamespaceParams) => {
      return createNewTeamForNamespac(namespace, name, description);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['organization', namespace, 'teams']);
      },
    },
  );

  return {
    createNewTeamHook: async (params: createNewTeamForNamespaceParams) =>
      createTeamMutator.mutate(params),
  };
}

interface createNewTeamForNamespaceParams {
  namespace: string;
  name: string;
  description: string;
}
