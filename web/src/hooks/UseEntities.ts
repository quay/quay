import {useEffect, useState} from 'react';
import {Entity, fetchEntities} from 'src/resources/UserResource';

export function useEntities(org: string, includeTeams?: boolean) {
  const [searchTerm, setSearchTerm] = useState<string>();
  const [isError, setIsError] = useState<boolean>();
  const [entities, setEntities] = useState<Entity[]>([]);

  const search = async () => {
    try {
      const entityResults = await fetchEntities(searchTerm, org, includeTeams);
      setEntities(entityResults);
    } catch (err) {
      setIsError(true);
    }
  };

  // If next character typed is under a second, don't fire the
  // request
  useEffect(() => {
    const delay = setTimeout(() => {
      if (searchTerm != null && searchTerm != '') {
        search();
      }
    }, 1000);
    return () => clearTimeout(delay);
  }, [searchTerm]);

  return {
    entities: !isError ? entities : [],
    isError: isError,
    searchTerm: searchTerm,
    setSearchTerm: setSearchTerm,
    setEntities: setEntities,
  };
}
