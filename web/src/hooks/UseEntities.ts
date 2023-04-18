import {useQuery} from '@tanstack/react-query';
import {useEffect, useState} from 'react';
import {Entity, fetchEntities} from 'src/resources/UserResource';

export function useEntities(org: string) {
  const [searchTerm, setSearchTerm] = useState<string>();
  const [isError, setIsError] = useState<boolean>();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const search = async () => {
    try {
      const entityResults = await fetchEntities(org, searchTerm);
      setLoading(false);
      setEntities(entityResults);
    } catch (err) {
      setLoading(false);
      setIsError(true);
    }
  };

  // If next character typed is under a second, don't fire the
  // request
  useEffect(() => {
    if (searchTerm != null && searchTerm != '') {
      setLoading(true);
      const delay = setTimeout(() => {
        search();
      }, 1000);
      return () => {
        setLoading(false);
        clearTimeout(delay);
      };
    } else {
      setEntities([]);
    }
  }, [searchTerm]);

  return {
    entities: !isError ? entities : [],
    isError: isError,
    isLoadingEntities: loading,
    searchTerm: searchTerm,
    setSearchTerm: setSearchTerm,
  };
}
