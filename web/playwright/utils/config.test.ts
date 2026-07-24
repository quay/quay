import {afterEach, describe, expect, test, vi} from 'vitest';
import {
  getApiUrl,
  getBaseUrl,
  getPlaywrightGrep,
  getPlaywrightWorkers,
  getQuayE2ETarget,
  getServiceCredentials,
  isServiceMode,
  requireServiceTargetAllowed,
} from './config';

const originalEnv = {...process.env};

describe('Playwright service target config', () => {
  afterEach(() => {
    process.env = {...originalEnv};
    vi.restoreAllMocks();
  });

  test('defaults to local target and local URLs', () => {
    delete process.env.QUAY_E2E_TARGET;
    delete process.env.PLAYWRIGHT_BASE_URL;
    delete process.env.REACT_QUAY_APP_API_URL;

    expect(getQuayE2ETarget()).toBe('local');
    expect(isServiceMode()).toBe(false);
    expect(getBaseUrl()).toBe('http://localhost:8080');
    expect(getApiUrl()).toBe('http://localhost:8080');
  });

  test('resolves stage target URLs', () => {
    process.env.QUAY_E2E_TARGET = 'stage';
    delete process.env.PLAYWRIGHT_BASE_URL;
    delete process.env.REACT_QUAY_APP_API_URL;

    expect(getQuayE2ETarget()).toBe('stage');
    expect(isServiceMode()).toBe(true);
    expect(getBaseUrl()).toBe('https://stage.quay.io');
    expect(getApiUrl()).toBe('https://stage.quay.io');
  });

  test('resolves prod target URLs only after explicit prod opt-in', () => {
    process.env.QUAY_E2E_TARGET = 'prod';
    delete process.env.QUAY_E2E_ALLOW_PROD;

    expect(() => requireServiceTargetAllowed()).toThrow(
      'QUAY_E2E_TARGET=prod requires QUAY_E2E_ALLOW_PROD=1',
    );

    process.env.QUAY_E2E_ALLOW_PROD = '1';

    expect(() => requireServiceTargetAllowed()).not.toThrow();
    expect(getBaseUrl()).toBe('https://quay.io');
    expect(getApiUrl()).toBe('https://quay.io');
  });

  test('requires explicit URLs for custom target', () => {
    process.env.QUAY_E2E_TARGET = 'custom';
    delete process.env.PLAYWRIGHT_BASE_URL;
    delete process.env.REACT_QUAY_APP_API_URL;

    expect(() => requireServiceTargetAllowed()).toThrow(
      'QUAY_E2E_TARGET=custom requires PLAYWRIGHT_BASE_URL or REACT_QUAY_APP_API_URL',
    );

    process.env.PLAYWRIGHT_BASE_URL = 'https://ui.example.test';

    expect(() => requireServiceTargetAllowed()).not.toThrow();
    expect(getBaseUrl()).toBe('https://ui.example.test');
    expect(getApiUrl()).toBe('https://ui.example.test');

    process.env.REACT_QUAY_APP_API_URL = 'https://api.example.test';

    expect(() => requireServiceTargetAllowed()).not.toThrow();
    expect(getBaseUrl()).toBe('https://ui.example.test');
    expect(getApiUrl()).toBe('https://api.example.test');
  });

  test('preserves original explicit URL overrides for local downstream runs', () => {
    delete process.env.QUAY_E2E_TARGET;
    process.env.OPENSHIFT_CI = '1';
    process.env.PLAYWRIGHT_BASE_URL = 'https://downstream-ui.example.test';
    process.env.REACT_QUAY_APP_API_URL = 'https://downstream-api.example.test';

    expect(getQuayE2ETarget()).toBe('local');
    expect(isServiceMode()).toBe(false);
    expect(getBaseUrl()).toBe('https://downstream-ui.example.test');
    expect(getApiUrl()).toBe('https://downstream-api.example.test');
    expect(getPlaywrightGrep()).toBeUndefined();
  });

  test('uses explicit base URL for service API calls when API URL is unset', () => {
    process.env.QUAY_E2E_TARGET = 'stage';
    process.env.PLAYWRIGHT_BASE_URL = 'https://stage-downstream.example.test';
    delete process.env.REACT_QUAY_APP_API_URL;

    expect(getBaseUrl()).toBe('https://stage-downstream.example.test');
    expect(getApiUrl()).toBe('https://stage-downstream.example.test');
  });

  test('allows explicit URLs to override service target defaults', () => {
    process.env.QUAY_E2E_TARGET = 'stage';
    process.env.PLAYWRIGHT_BASE_URL = 'https://stage-ui.example.test';
    process.env.REACT_QUAY_APP_API_URL = 'https://stage-api.example.test';

    expect(getBaseUrl()).toBe('https://stage-ui.example.test');
    expect(getApiUrl()).toBe('https://stage-api.example.test');
  });

  test('rejects unknown targets', () => {
    process.env.QUAY_E2E_TARGET = 'staging';

    expect(() => getQuayE2ETarget()).toThrow(
      'QUAY_E2E_TARGET must be one of local, stage, prod, custom',
    );
  });

  test('defaults service runs to @service-safe and one worker', () => {
    process.env.QUAY_E2E_TARGET = 'stage';
    delete process.env.PLAYWRIGHT_GREP;
    delete process.env.PLAYWRIGHT_WORKERS;

    expect(getPlaywrightGrep()).toBe('@service-safe');
    expect(getPlaywrightWorkers()).toBe(1);
  });

  test('allows explicit grep and worker overrides in service mode', () => {
    process.env.QUAY_E2E_TARGET = 'stage';
    process.env.PLAYWRIGHT_GREP = '@service-safe|@smoke';
    process.env.PLAYWRIGHT_WORKERS = '2';

    expect(getPlaywrightGrep()).toBe('@service-safe|@smoke');
    expect(getPlaywrightWorkers()).toBe(2);
  });

  test('warns and falls back when explicit workers are invalid', () => {
    process.env.QUAY_E2E_TARGET = 'stage';
    process.env.PLAYWRIGHT_WORKERS = 'invalid';
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);

    expect(getPlaywrightWorkers()).toBe(1);
    expect(warn).toHaveBeenCalledWith(
      'Ignoring invalid PLAYWRIGHT_WORKERS="invalid"; expected a positive integer.',
    );
  });

  test('reads optional service user credentials from env', () => {
    process.env.QUAY_E2E_USERNAME = 'service-user';
    process.env.QUAY_E2E_PASSWORD = 'service-password';
    process.env.QUAY_E2E_TOKEN = 'service-token';

    expect(getServiceCredentials()).toEqual({
      username: 'service-user',
      password: 'service-password',
      token: 'service-token',
    });
  });
});
