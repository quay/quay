// @vitest-environment node

import {afterEach, beforeEach, describe, expect, it} from 'vitest';
import {
  applyChromiumLoopbackBypass,
  proxyOptionFromEnv,
  proxyServerFromEnv,
} from './proxy';

const PROXY_ENV_KEYS = [
  'HTTP_PROXY',
  'http_proxy',
  'HTTPS_PROXY',
  'https_proxy',
  'NO_PROXY',
  'no_proxy',
  'PLAYWRIGHT_BASE_URL',
  'REACT_QUAY_APP_API_URL',
  'PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK',
] as const;

const originalValues = new Map(
  PROXY_ENV_KEYS.map((key) => [key, process.env[key]]),
);

beforeEach(() => {
  for (const key of PROXY_ENV_KEYS) delete process.env[key];
});

afterEach(() => {
  for (const key of PROXY_ENV_KEYS) {
    const originalValue = originalValues.get(key);
    if (originalValue === undefined) delete process.env[key];
    else process.env[key] = originalValue;
  }
});

describe('proxyOptionFromEnv', () => {
  it('selects the proxy matching the configured target scheme', () => {
    process.env.HTTP_PROXY = 'http://http-proxy:3128';
    process.env.HTTPS_PROXY = 'http://https-proxy:3128';

    process.env.REACT_QUAY_APP_API_URL = 'https://quay.example.test';
    expect(proxyServerFromEnv()).toBe('http://https-proxy:3128');

    process.env.REACT_QUAY_APP_API_URL = 'http://quay.example.test';
    expect(proxyServerFromEnv()).toBe('http://http-proxy:3128');
  });

  it('separates URL credentials and expands plain hostname bypasses', () => {
    process.env.HTTP_PROXY =
      'http://test-user:test-password@proxy.example.test:3128';
    process.env.NO_PROXY = 'quay.example.test,localhost,10.0.0.1';

    expect(proxyOptionFromEnv()).toEqual({
      server: 'http://proxy.example.test:3128',
      username: 'test-user',
      password: 'test-password',
      bypass: 'quay.example.test,.quay.example.test,localhost,10.0.0.1',
    });
  });

  it('does not configure a proxy when NO_PROXY bypasses every host', () => {
    process.env.HTTP_PROXY = 'http://proxy.example.test:3128';
    process.env.NO_PROXY = '*';

    expect(proxyOptionFromEnv()).toBeUndefined();
  });
});

describe('applyChromiumLoopbackBypass', () => {
  it('keeps loopback direct when a proxy is configured', () => {
    process.env.HTTP_PROXY = 'http://proxy.example.test:3128';

    applyChromiumLoopbackBypass();

    expect(
      process.env.PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK,
    ).toBe('1');
  });

  it('preserves an explicit loopback setting', () => {
    process.env.HTTP_PROXY = 'http://proxy.example.test:3128';
    process.env.PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK = '0';

    applyChromiumLoopbackBypass();

    expect(
      process.env.PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK,
    ).toBe('0');
  });
});
