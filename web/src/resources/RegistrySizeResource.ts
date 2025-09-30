import axios from 'src/libs/axios';

export interface IRegistrySize {
  size_bytes: number;
  last_ran: number | null;
  queued: boolean;
  running: boolean;
}

// Get registry size data
export async function fetchRegistrySize(): Promise<IRegistrySize> {
  const response = await axios.get('/api/v1/superuser/registrysize/');
  return response.data;
}

// Queue registry size calculation
export async function queueRegistrySizeCalculation(): Promise<void> {
  await axios.post('/api/v1/superuser/registrysize/');
}
