import {useEffect, useState} from 'react';
import {fetchRepositoriesForNamespace} from 'src/resources/RepositoryResource';

export default function RepoCount(props: RepoCountProps) {
  const [value, setValue] = useState<string>('Loading...');
  useEffect(() => {
    (async () => {
      try {
        const data = await fetchRepositoriesForNamespace(props.name);
        setValue(data.length);
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
