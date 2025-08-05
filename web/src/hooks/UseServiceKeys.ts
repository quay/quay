import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import React, {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {
  fetchServiceKeys,
  createServiceKey,
  updateServiceKey,
  deleteServiceKey,
  approveServiceKey,
  CreateServiceKeyRequest,
  UpdateServiceKeyRequest,
  IServiceKey,
} from 'src/resources/ServiceKeysResource';

// Using local state for search - can be moved to Recoil atoms later if needed
const dummySearchState = {
  query: '',
  field: 'name',
};

export function useServiceKeys() {
  // Keep state of current search and pagination
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState<SearchState>(dummySearchState);

  // Sorting state
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(null);
  const [activeSortDirection, setActiveSortDirection] = useState<
    'asc' | 'desc' | null
  >(null);

  // Fetch service keys data
  const {
    data: serviceKeys = [],
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: ['serviceKeys'],
    queryFn: fetchServiceKeys,
  });

  // Apply search filter
  const filteredKeys = search.query
    ? serviceKeys.filter((key) => {
        const searchQuery = search.query.toLowerCase();
        return (
          (key.name && key.name.toLowerCase().includes(searchQuery)) ||
          key.service.toLowerCase().includes(searchQuery) ||
          key.kid.toLowerCase().includes(searchQuery)
        );
      })
    : serviceKeys;

  // Get sortable row values for a service key
  const getSortableRowValues = (key: IServiceKey): (string | number)[] => {
    return [
      '', // Column 0: expand/collapse
      '', // Column 1: checkbox
      key.name?.toLowerCase() || '', // Column 2: name
      key.service.toLowerCase(), // Column 3: service
      new Date(key.created_date).getTime(), // Column 4: created_date
      key.expiration_date ? new Date(key.expiration_date).getTime() : 0, // Column 5: expiration_date
    ];
  };

  // Apply sorting based on PatternFly pattern
  const sortedKeys =
    activeSortIndex !== null && activeSortDirection
      ? [...filteredKeys].sort((a, b) => {
          const aValue = getSortableRowValues(a)[activeSortIndex];
          const bValue = getSortableRowValues(b)[activeSortIndex];

          if (activeSortDirection === 'asc') {
            return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
          } else {
            return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
          }
        })
      : filteredKeys;

  // Apply pagination
  const paginatedKeys = sortedKeys.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  // Get query client for mutations
  const queryClient = useQueryClient();

  // Create service key mutation
  const createServiceKeyMutator = useMutation({
    mutationFn: (keyData: CreateServiceKeyRequest) => createServiceKey(keyData),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['serviceKeys']});
    },
  });

  // Update service key mutation
  const updateServiceKeyMutator = useMutation({
    mutationFn: ({
      kid,
      keyData,
    }: {
      kid: string;
      keyData: UpdateServiceKeyRequest;
    }) => updateServiceKey(kid, keyData),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['serviceKeys']});
    },
  });

  // Delete service key mutation
  const deleteServiceKeyMutator = useMutation({
    mutationFn: (kid: string) => deleteServiceKey(kid),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['serviceKeys']});
    },
  });

  // Approve service key mutation
  const approveServiceKeyMutator = useMutation({
    mutationFn: (kid: string) => approveServiceKey(kid),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['serviceKeys']});
    },
  });

  // Bulk delete mutation
  const bulkDeleteMutator = useMutation({
    mutationFn: async (kids: string[]) => {
      await Promise.all(kids.map((kid) => deleteServiceKey(kid)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['serviceKeys']});
    },
  });

  // Sort handler function following PatternFly pattern
  const handleSort = (
    _event: React.MouseEvent,
    index: number,
    direction: 'asc' | 'desc',
  ) => {
    setActiveSortIndex(index);
    setActiveSortDirection(direction);
    // Reset to first page when sorting changes
    setPage(1);
  };

  return {
    // Data
    serviceKeys,
    filteredKeys: sortedKeys,
    paginatedKeys,

    // State
    loading,
    error,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
    activeSortIndex,
    activeSortDirection,
    handleSort,

    // Metadata
    totalResults: sortedKeys.length,

    // Mutations
    createServiceKey: (keyData: CreateServiceKeyRequest) =>
      createServiceKeyMutator.mutate(keyData),
    updateServiceKey: (kid: string, keyData: UpdateServiceKeyRequest) =>
      updateServiceKeyMutator.mutate({kid, keyData}),
    deleteServiceKey: (kid: string) => deleteServiceKeyMutator.mutate(kid),
    approveServiceKey: (kid: string) => approveServiceKeyMutator.mutate(kid),
    bulkDeleteKeys: (kids: string[]) => bulkDeleteMutator.mutate(kids),

    // Mutation states
    isCreating: createServiceKeyMutator.isLoading,
    isUpdating: updateServiceKeyMutator.isLoading,
    isDeleting: deleteServiceKeyMutator.isLoading,
    isApproving: approveServiceKeyMutator.isLoading,
    isBulkDeleting: bulkDeleteMutator.isLoading,
  };
}
