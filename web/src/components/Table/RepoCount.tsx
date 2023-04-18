import {useEffect, useState} from 'react';
import {useRepositories} from 'src/hooks/UseRepositories';

export default function RepoCount(props: RepoCountProps) {
  const [value, setValue] = useState<string>('Loading...');
  const {totalResults} = useRepositories(props.name);

  useEffect(() => {
    (async () => {
      try {
        setValue(totalResults.toString());
      } catch (err) {
        setValue('Error');
      }
    })();
  }, []);
  return <>{value}</>;
}

interface RepoCountProps {
  name: string;
}
