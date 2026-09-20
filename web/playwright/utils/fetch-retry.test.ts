// @vitest-environment node

import {describe, expect, it, vi} from 'vitest';
import {
  fetchJsonWithRetry,
  fetchWithRetry,
  FetchRetryExhaustedError,
} from './fetch-retry';

describe('fetchJsonWithRetry', () => {
  it('retries a 200 whose .json() rejects and succeeds on a later attempt', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => {
            throw new Error('Unexpected end of JSON input');
          },
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({hello: 'world'}),
        });
      vi.stubGlobal('fetch', fetchFn);

      const resultPromise = fetchJsonWithRetry<{hello: string}>(
        'test',
        'http://example.com',
      );
      await vi.runAllTimersAsync();
      const result = await resultPromise;

      expect(result).toEqual({hello: 'world'});
      expect(fetchFn).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });

  it('returns the parsed body on first success, one fetch call', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({hello: 'world'}),
    });
    vi.stubGlobal('fetch', fetchFn);
    try {
      const result = await fetchJsonWithRetry<{hello: string}>(
        'test',
        'http://example.com',
      );
      expect(result).toEqual({hello: 'world'});
      expect(fetchFn).toHaveBeenCalledTimes(1);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('exhaustion on a persistently unparseable 200 throws with receivedResponse true', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('Unexpected end of JSON input');
        },
      });
      vi.stubGlobal('fetch', fetchFn);

      const resultPromise = fetchJsonWithRetry('test', 'http://example.com');
      resultPromise.catch(() => {
        // Assertion runs below; prevent an unhandled-rejection warning
        // between promise creation and the timer flush.
      });
      await vi.runAllTimersAsync();
      let caught: FetchRetryExhaustedError | undefined;
      try {
        await resultPromise;
      } catch (err) {
        caught = err as FetchRetryExhaustedError;
      }

      expect(caught?.receivedResponse).toBe(true);
      expect(fetchFn).toHaveBeenCalledTimes(3);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });
});

describe('fetchWithRetry', () => {
  it('retries a 500 and then succeeds', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi
        .fn()
        .mockResolvedValueOnce({ok: false, status: 500})
        .mockResolvedValueOnce({ok: true, status: 200});
      vi.stubGlobal('fetch', fetchFn);

      const resultPromise = fetchWithRetry('test', 'http://example.com');
      await vi.runAllTimersAsync();
      const result = await resultPromise;

      expect(result.ok).toBe(true);
      expect(fetchFn).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });

  it('retries a thrown network error and then succeeds', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi
        .fn()
        .mockRejectedValueOnce(new Error('ECONNREFUSED'))
        .mockResolvedValueOnce({ok: true, status: 200});
      vi.stubGlobal('fetch', fetchFn);

      const resultPromise = fetchWithRetry('test', 'http://example.com');
      await vi.runAllTimersAsync();
      const result = await resultPromise;

      expect(result.ok).toBe(true);
      expect(fetchFn).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });
});
