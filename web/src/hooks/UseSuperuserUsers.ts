import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {bulkDeleteUsers, createUser, fetchSuperuserUsers} from 'src/resources/SuperuserUsersResource';
import {superuserUsersColumnNames} from 'src/routes/SuperuserList/Users/SuperuserUsersList';
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
    field: superuserUsersColumnNames.username,
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


export function useCreateUser({onSuccess, onError}) {
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


export function useDeleteUser( {onSuccess, onError}) {
  const queryClient = useQueryClient();
  const deleteUsersMutator = useMutation(
    async (users: ISuperuserUsers[] | ISuperuserUsers) => {
      users = Array.isArray(users) ? users : [users];
      return bulkDeleteUsers(users);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['superuserusers']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );
  return {
    removeUser: async (users: ISuperuserUsers[] | ISuperuserUsers) =>
      deleteUsersMutator.mutate(users),
  };
}
