// @vitest-environment node

import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

// s3.ts promisifies exec/execFile at import time; these mocks follow the
// callback convention, so the promisified call resolves with {stdout, stderr}.
const {exec, execFile} = vi.hoisted(() => ({
  exec: vi.fn(),
  execFile: vi.fn(),
}));
vi.mock('child_process', () => ({exec, execFile}));

type Callback = (
  err: Error | null,
  out?: {stdout: string; stderr: string},
) => void;

function succeed(stdout = '') {
  return (...args: unknown[]) =>
    (args[args.length - 1] as Callback)(null, {stdout, stderr: ''});
}

function fail(stderr: string) {
  return (...args: unknown[]) =>
    (args[args.length - 1] as Callback)(
      Object.assign(new Error('Command failed: aws'), {stderr}),
    );
}

// S3_ENDPOINT and S3_REGION are read when s3.ts is loaded, so each test
// imports a fresh copy after setting the environment.
async function loadS3() {
  vi.resetModules();
  return import('./s3');
}

beforeEach(() => {
  exec.mockReset();
  execFile.mockReset();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('getStorageBuckets / getPrimaryBucket', () => {
  it('defaults to the CI geo-replication buckets when S3_BUCKETS is unset', async () => {
    vi.stubEnv('S3_BUCKETS', undefined);
    const s3 = await loadS3();
    expect(s3.getStorageBuckets()).toEqual(['quay-us-east', 'quay-eu-west']);
    expect(s3.getPrimaryBucket()).toBe('quay-us-east');
  });

  it('parses a custom list, trimming names and dropping empty entries', async () => {
    vi.stubEnv('S3_BUCKETS', ' quay-registry , ,second,');
    const s3 = await loadS3();
    expect(s3.getStorageBuckets()).toEqual(['quay-registry', 'second']);
    expect(s3.getPrimaryBucket()).toBe('quay-registry');
  });

  it('accepts a single bucket', async () => {
    vi.stubEnv('S3_BUCKETS', 'quay-registry');
    const s3 = await loadS3();
    expect(s3.getStorageBuckets()).toEqual(['quay-registry']);
  });

  it.each(['', ' ', ', ,'])(
    'falls back to the defaults when S3_BUCKETS is %j',
    async (value) => {
      vi.stubEnv('S3_BUCKETS', value);
      const s3 = await loadS3();
      expect(s3.getStorageBuckets()).toEqual(['quay-us-east', 'quay-eu-west']);
    },
  );
});

describe('getStoragePath / blobKey', () => {
  const digest =
    'sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789';
  const hash = digest.replace('sha256:', '');

  it.each([
    [undefined, 'datastorage/registry'],
    ['/datastorage/registry/', 'datastorage/registry'],
    ['custom/path', 'custom/path'],
    ['', ''],
    ['/', ''],
    ['///', ''],
  ])('S3_STORAGE_PATH %j gives storage path %j', async (value, expected) => {
    vi.stubEnv('S3_STORAGE_PATH', value);
    const s3 = await loadS3();
    expect(s3.getStoragePath()).toBe(expected);
  });

  it('prefixes the key with the default storage path', async () => {
    vi.stubEnv('S3_STORAGE_PATH', undefined);
    const s3 = await loadS3();
    expect(s3.blobKey(digest)).toBe(`datastorage/registry/sha256/ab/${hash}`);
  });

  it.each(['', '/'])(
    'starts the key at sha256/ for a root storage path %j',
    async (value) => {
      vi.stubEnv('S3_STORAGE_PATH', value);
      const s3 = await loadS3();
      expect(s3.blobKey(digest)).toBe(`sha256/ab/${hash}`);
    },
  );
});

describe('isS3Configured', () => {
  it('is false without S3_ENDPOINT and does not call the aws CLI', async () => {
    vi.stubEnv('S3_ENDPOINT', undefined);
    const s3 = await loadS3();
    await expect(s3.isS3Configured()).resolves.toBe(false);
    expect(exec).not.toHaveBeenCalled();
  });

  it('is true with S3_ENDPOINT when the aws CLI is available', async () => {
    vi.stubEnv('S3_ENDPOINT', 'http://s3.example.com:3900');
    exec.mockImplementation(succeed('aws-cli/2.0.0'));
    const s3 = await loadS3();
    await expect(s3.isS3Configured()).resolves.toBe(true);
  });

  it('is false with S3_ENDPOINT when the aws CLI is missing', async () => {
    vi.stubEnv('S3_ENDPOINT', 'http://s3.example.com:3900');
    exec.mockImplementation(fail('aws: command not found'));
    const s3 = await loadS3();
    await expect(s3.isS3Configured()).resolves.toBe(false);
  });
});

describe('headObject', () => {
  const bucket = 'quay-registry';
  const key = 'datastorage/registry/sha256/40/404abc';

  beforeEach(() => {
    vi.stubEnv('S3_ENDPOINT', 'http://s3.example.com:3900');
    vi.stubEnv('S3_REGION', 'us-east-1');
  });

  it('returns the object size and calls the aws CLI without a shell', async () => {
    execFile.mockImplementation(succeed(JSON.stringify({ContentLength: 1234})));
    const s3 = await loadS3();

    await expect(s3.headObject(bucket, key)).resolves.toEqual({size: 1234});
    expect(execFile).toHaveBeenCalledTimes(1);
    const [file, args] = execFile.mock.calls[0];
    expect(file).toBe('aws');
    expect(args).toEqual([
      '--endpoint-url',
      'http://s3.example.com:3900',
      '--region',
      'us-east-1',
      's3api',
      'head-object',
      '--bucket',
      bucket,
      '--key',
      key,
      '--output',
      'json',
    ]);
  });

  it.each([
    'An error occurred (404) when calling the HeadObject operation: Not Found',
    'An error occurred (NoSuchKey) when calling the HeadObject operation',
  ])(
    'returns null for a missing object once head-bucket confirms the bucket (%s)',
    async (stderr) => {
      execFile
        .mockImplementationOnce(fail(stderr))
        .mockImplementationOnce(succeed());
      const s3 = await loadS3();

      await expect(s3.headObject(bucket, key)).resolves.toBeNull();
      expect(execFile).toHaveBeenCalledTimes(2);
      expect(execFile.mock.calls[1][1]).toEqual(
        expect.arrayContaining(['head-bucket', '--bucket', bucket]),
      );
    },
  );

  it('throws when the 404 comes from a missing bucket', async () => {
    execFile
      .mockImplementationOnce(
        fail(
          'An error occurred (404) when calling the HeadObject operation: Not Found',
        ),
      )
      .mockImplementationOnce(
        fail(
          'An error occurred (404) when calling the HeadBucket operation: Not Found',
        ),
      );
    const s3 = await loadS3();

    await expect(s3.headObject('no-such-bucket', key)).rejects.toThrow();
  });

  it('rethrows other errors without checking the bucket', async () => {
    execFile.mockImplementation(
      fail(
        'An error occurred (403) when calling the HeadObject operation: Forbidden',
      ),
    );
    const s3 = await loadS3();

    // The key contains "404"; only stderr decides whether the object is missing.
    await expect(s3.headObject(bucket, key)).rejects.toThrow();
    expect(execFile).toHaveBeenCalledTimes(1);
  });
});
