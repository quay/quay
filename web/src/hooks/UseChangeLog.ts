import {useQuery} from '@tanstack/react-query';
import {fetchChangeLog} from 'src/resources/ChangeLogResource';

export function useChangeLog() {
  const result = useQuery({
    queryKey: ['changeLog'],
    queryFn: async () => {
      return await fetchChangeLog();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - change log doesn't update frequently
  });

  return {
    ...result,
    changeLog: result.data,
  };
}
