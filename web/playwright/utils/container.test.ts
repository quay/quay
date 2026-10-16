// @vitest-environment node

import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {retryOperation} from './container';

const SKOPEO_503 =
  'Command failed: skopeo copy\ntime="2026-10-08T02:51:25Z" level=fatal msg="copying system image from manifest list: writing blob: uploading layer to https://quay.example.com/v2/testuser/repo/blobs/uploads/72e5ddf1?digest=sha256%3A487858d29734ed603b5bd86f96a8d2e3bee39a06736bad6a93493b3a8ad0500f: received unexpected HTTP status: 503 SERVICE UNAVAILABLE"';

describe('retryOperation', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('throws a registry 5xx after one attempt', async () => {
    const operation = vi.fn().mockRejectedValue(new Error(SKOPEO_503));

    const result = expect(retryOperation(operation)).rejects.toThrow(
      `registry returned HTTP 5xx: ${SKOPEO_503}`,
    );
    await vi.runAllTimersAsync();
    await result;

    expect(operation).toHaveBeenCalledTimes(1);
  });

  it('throws a 5xx reason phrase without "status" after one attempt', async () => {
    const message =
      'PUT https://quay.example.com/v2/org/repo/manifests/latest: 501 Not Implemented';
    const operation = vi.fn().mockRejectedValue(new Error(message));

    const result = expect(retryOperation(operation)).rejects.toThrow(
      `registry returned HTTP 5xx: ${message}`,
    );
    await vi.runAllTimersAsync();
    await result;

    expect(operation).toHaveBeenCalledTimes(1);
  });

  it('retries a transient EOF whose port and digest contain 5xx', async () => {
    const operation = vi
      .fn()
      .mockRejectedValueOnce(
        new Error(
          'Get "https://quay.example.com:5000/v2/org/repo/blobs/sha256:5003a1c0ffee503": EOF',
        ),
      )
      .mockResolvedValueOnce(undefined);

    const result = retryOperation(operation);
    await vi.runAllTimersAsync();
    await result;

    expect(operation).toHaveBeenCalledTimes(2);
  });

  it('retries a non-5xx error up to maxAttempts, then rethrows it', async () => {
    const err = new Error('received unexpected HTTP status: 401 Unauthorized');
    const operation = vi.fn().mockRejectedValue(err);

    const result = expect(retryOperation(operation, 3)).rejects.toBe(err);
    await vi.runAllTimersAsync();
    await result;

    expect(operation).toHaveBeenCalledTimes(3);
  });
});
