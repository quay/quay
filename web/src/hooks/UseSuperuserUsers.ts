import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {createUser, fetchSuperuserUsers} from 'src/resources/SuperuserResource';
import {superuserUsersViewColumnNames} from 'src/routes/SuperuserList/Users/SuperuserUsersList';
import {useCurrentUser} from './UseCurrentUser';

export interface ISuperuserUsers {
  kind: string;
  name: string;
  username: string;
  email: string;
  super_user: boolean;
  enabled: boolean;
}

export function useFetchSuperuserUsers() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: superuserUsersViewColumnNames.username,
  });
  const {isSuperUser} = useCurrentUser();

  const {
    data: users,
    isLoading,
    isPlaceholderData,
    isError: errorLoadingUsers,
  } = useQuery<ISuperuserUsers[]>(
    ['superuserusers'],
    () => fetchSuperuserUsers(),
    {
      placeholderData: [],
      enabled: isSuperUser || true,
    },
  );

  const filteredUsers =
    search.query !== ''
      ? users?.filter((user) => user.username.includes(search.query))
      : users;

  const paginatedUsers = filteredUsers?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    users,
    filteredUsers,
    paginatedUsers,
    isLoadingUsers: isLoading || isPlaceholderData,
    errorLoadingUsers,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}


export function useCreate({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const createUserMutator = useMutation(
    async ({name, email}: {name: string; email: string}) => {
      return createUser(name, email);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['superuserusers']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    createUser: async (name: string, email: string) =>
      createUserMutator.mutate({name, email}),
  };
}
