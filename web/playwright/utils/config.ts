/**
 * Global configuration for Playwright tests
 */

const LOCAL_URL = 'http://localhost:8080';
const SERVICE_SAFE_GREP = '@service-safe';

export type QuayE2ETarget = 'local' | 'stage' | 'prod' | 'custom';

const TARGET_DEFAULT_URLS: Partial<Record<QuayE2ETarget, string>> = {
  local: LOCAL_URL,
  stage: 'https://stage.quay.io',
  prod: 'https://quay.io',
};

const VALID_TARGETS: QuayE2ETarget[] = ['local', 'stage', 'prod', 'custom'];

// Backend API URL (registry + API)
export const API_URL = getApiUrl();

// Frontend URL
export const BASE_URL = getBaseUrl();

export interface ServiceCredentials {
  username?: string;
  password?: string;
  token?: string;
}

export function getQuayE2ETarget(): QuayE2ETarget {
  const target = (process.env.QUAY_E2E_TARGET || 'local').toLowerCase();
  if (VALID_TARGETS.includes(target as QuayE2ETarget)) {
    return target as QuayE2ETarget;
  }

  throw new Error('QUAY_E2E_TARGET must be one of local, stage, prod, custom');
}

export function isServiceMode(): boolean {
  return getQuayE2ETarget() !== 'local';
}

function getTargetDefaultUrl(): string | undefined {
  return TARGET_DEFAULT_URLS[getQuayE2ETarget()];
}

function requireCustomUrls(): void {
  if (getQuayE2ETarget() !== 'custom') return;

  const missing = [
    !process.env.PLAYWRIGHT_BASE_URL && 'PLAYWRIGHT_BASE_URL',
    !process.env.REACT_QUAY_APP_API_URL && 'REACT_QUAY_APP_API_URL',
  ].filter(Boolean);

  if (missing.length > 0) {
    throw new Error(
      `QUAY_E2E_TARGET=custom requires external URL env: ${missing.join(', ')}`,
    );
  }
}

export function requireServiceTargetAllowed(): void {
  const target = getQuayE2ETarget();

  if (target === 'prod' && process.env.QUAY_E2E_ALLOW_PROD !== '1') {
    throw new Error('QUAY_E2E_TARGET=prod requires QUAY_E2E_ALLOW_PROD=1');
  }

  requireCustomUrls();
}

export function getApiUrl(): string {
  if (process.env.REACT_QUAY_APP_API_URL) {
    return process.env.REACT_QUAY_APP_API_URL;
  }

  const defaultUrl = getTargetDefaultUrl();
  if (defaultUrl) return defaultUrl;

  requireCustomUrls();
  return process.env.REACT_QUAY_APP_API_URL!;
}

export function getBaseUrl(): string {
  if (process.env.PLAYWRIGHT_BASE_URL) {
    return process.env.PLAYWRIGHT_BASE_URL;
  }

  const defaultUrl = getTargetDefaultUrl();
  if (defaultUrl) return defaultUrl;

  requireCustomUrls();
  return process.env.PLAYWRIGHT_BASE_URL!;
}

export function getPlaywrightGrep(): string | undefined {
  if (process.env.PLAYWRIGHT_GREP) {
    return process.env.PLAYWRIGHT_GREP;
  }

  return isServiceMode() ? SERVICE_SAFE_GREP : undefined;
}

export function getPlaywrightWorkers(): number | undefined {
  const explicitWorkers = process.env.PLAYWRIGHT_WORKERS;
  if (explicitWorkers) {
    const parsed = Number.parseInt(explicitWorkers, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      return parsed;
    }
  }

  if (isServiceMode()) {
    return 1;
  }

  return process.env.CI ? 4 : undefined;
}

export function getServiceCredentials(): ServiceCredentials {
  return {
    username: process.env.QUAY_E2E_USERNAME,
    password: process.env.QUAY_E2E_PASSWORD,
    token: process.env.QUAY_E2E_TOKEN,
  };
}

export function requireServiceUserCredentials(): {
  username: string;
  password: string;
  token?: string;
} {
  const credentials = getServiceCredentials();
  if (!credentials.username || !credentials.password) {
    throw new Error(
      'Service authenticated fixtures require QUAY_E2E_USERNAME and QUAY_E2E_PASSWORD',
    );
  }

  return {
    username: credentials.username,
    password: credentials.password,
    token: credentials.token,
  };
}
