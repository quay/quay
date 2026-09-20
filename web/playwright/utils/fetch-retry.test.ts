// @vitest-environment node

import {describe, expect, it, vi} from 'vitest';
import {
  fetchJsonWithRetry,
  fetchWithRetry,
  FetchRetryExhaustedError,
} from './fetch-retry';
import {mailpit} from './mailpit';

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

  it('fails fast on a 404: exactly one fetch call', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ok: false, status: 404});
    vi.stubGlobal('fetch', fetchFn);
    try {
      let caught: FetchRetryExhaustedError | undefined;
      try {
        await fetchJsonWithRetry('test', 'http://example.com');
      } catch (err) {
        caught = err as FetchRetryExhaustedError;
      }
      expect(caught).toBeDefined();
      expect(caught?.receivedResponse).toBe(true);
      expect(fetchFn).toHaveBeenCalledTimes(1);
    } finally {
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

  it('fails fast on a 404: exactly one fetch call, receivedResponse is true', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ok: false, status: 404});
    vi.stubGlobal('fetch', fetchFn);
    try {
      let caught: FetchRetryExhaustedError | undefined;
      try {
        await fetchWithRetry('test', 'http://example.com');
      } catch (err) {
        caught = err as FetchRetryExhaustedError;
      }
      expect(caught).toBeDefined();
      expect(caught?.receivedResponse).toBe(true);
      expect(fetchFn).toHaveBeenCalledTimes(1);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('retries a 429 (one fetch call is not enough)', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi
        .fn()
        .mockResolvedValueOnce({ok: false, status: 429})
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

  it('retries a 408 (one fetch call is not enough)', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi
        .fn()
        .mockResolvedValueOnce({ok: false, status: 408})
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

  it('exhaustion throws with receivedResponse reflecting whether any response was received', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi.fn().mockRejectedValue(new Error('offline'));
      vi.stubGlobal('fetch', fetchFn);

      const resultPromise = fetchWithRetry('test', 'http://example.com');
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

      expect(caught?.receivedResponse).toBe(false);
      expect(fetchFn).toHaveBeenCalledTimes(3);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });

  it('exhaustion throws with receivedResponse true when every attempt got a retryable error response', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi.fn().mockResolvedValue({ok: false, status: 500});
      vi.stubGlobal('fetch', fetchFn);

      const resultPromise = fetchWithRetry('test', 'http://example.com');
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

describe('mailpit.isAvailable contract', () => {
  it('returns false on a consistent 404', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ok: false, status: 404});
    vi.stubGlobal('fetch', fetchFn);
    try {
      await expect(mailpit.isAvailable()).resolves.toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('rethrows on a thrown connect error', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi.fn().mockRejectedValue(new Error('ECONNREFUSED'));
      vi.stubGlobal('fetch', fetchFn);

      const resultPromise = mailpit.isAvailable();
      resultPromise.catch(() => {
        // Rejection assertion runs below; prevent an unhandled-rejection
        // warning between promise creation and the timer flush.
      });
      await vi.runAllTimersAsync();
      let caught: FetchRetryExhaustedError | undefined;
      try {
        await resultPromise;
      } catch (err) {
        caught = err as FetchRetryExhaustedError;
      }
      expect(caught).toBeDefined();
      expect(caught?.receivedResponse).toBe(false);
      expect((caught?.cause as Error)?.message).toBe('ECONNREFUSED');
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });
});
