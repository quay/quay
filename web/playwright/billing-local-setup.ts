import type {QuayConfig} from './fixtures';
import {API_URL} from './utils/config';
import {fetchJsonWithRetry} from './utils/fetch-retry';

export default async function billingLocalSetup() {
  const config = await fetchJsonWithRetry<QuayConfig>(
    'billing configuration',
    `${API_URL}/config`,
  );
  process.env.QUAY_CONFIG_JSON = JSON.stringify(config);
}
