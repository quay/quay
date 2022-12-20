import {useEffect, useRef, useState} from 'react';
import axios from 'src/libs/axios';

export function useAxios<T>(method: string, url: string, payload: any) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);
  const controllerRef = useRef(new AbortController());
  const cancel = () => {
    controllerRef.current.abort();
  };
  useEffect(() => {
    (async () => {
      try {
        const response = await axios.request({
          data: payload,
          signal: controllerRef.current.signal,
          method,
          url,
        });
        setData(response.data);
      } catch (error: any) {
        setError(error.message);
      } finally {
        setLoaded(true);
      }
    })();
  }, []);
  return [data, loaded, error, cancel];
}
