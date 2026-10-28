// @vitest-environment node

import {EventEmitter} from 'events';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

// container.ts promisifies execFile at import time; this mock follows the
// callback convention, so the promisified call resolves with {stdout, stderr}.
const {execFile, spawn} = vi.hoisted(() => ({
  execFile: vi.fn(),
  spawn: vi.fn(),
}));
vi.mock('child_process', () => ({execFile, execFileSync: vi.fn(), spawn}));

// regctl login runs through spawn; exit 0 once stdin is written.
function fakeChild() {
  const child = Object.assign(new EventEmitter(), {
    stderr: {setEncoding: vi.fn(), on: vi.fn()},
    stdin: {end: () => setImmediate(() => child.emit('close', 0))},
  });
  return child;
}

// REGCTL_TLS is derived from API_URL when container.ts is loaded, so each
// test imports a fresh copy after setting the environment.
async function loadContainer() {
  vi.resetModules();
  return import('./container');
}

beforeEach(() => {
  execFile.mockReset();
  execFile.mockImplementation((...args: unknown[]) =>
    (args[args.length - 1] as (err: null, out: object) => void)(null, {
      stdout: '',
      stderr: '',
    }),
  );
  spawn.mockReset();
  spawn.mockImplementation(fakeChild);
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('regctlListTags', () => {
  it.each([
    ['https://quay.example.com', 'quay.example.com', 'insecure'],
    ['http://localhost:8080', 'localhost:8080', 'disabled'],
  ])('registry set for %s (host %s) uses --tls %s', async (url, host, tls) => {
    vi.stubEnv('REACT_QUAY_APP_API_URL', url);
    const {regctlListTags} = await loadContainer();

    await regctlListTags('org', 'repo', 'user', 'pass');

    expect(execFile).toHaveBeenCalledWith(
      'regctl',
      ['registry', 'set', host, '--tls', tls, '--skip-check'],
      expect.anything(),
      expect.any(Function),
    );
  });
});
