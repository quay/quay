// @vitest-environment node

import {describe, expect, it, vi} from 'vitest';
import type {TestInfo} from '@playwright/test';
import {writeFile} from 'fs/promises';
import {
  attachFailureArtifacts,
  collectJaegerSpans,
  newTraceContext,
  shouldCollect,
} from './failure-artifacts';

vi.mock('fs/promises', () => ({
  writeFile: vi.fn().mockResolvedValue(undefined),
}));

describe('newTraceContext', () => {
  it('produces a well-formed W3C trace context', () => {
    const trace = newTraceContext();
    expect(trace.traceId).toMatch(/^[0-9a-f]{32}$/);
    expect(trace.spanId).toMatch(/^[0-9a-f]{16}$/);
    expect(trace.traceparent).toBe(`00-${trace.traceId}-${trace.spanId}-01`);
  });

  it('mints a different trace id on each call', () => {
    const a = newTraceContext();
    const b = newTraceContext();
    expect(a.traceId).not.toBe(b.traceId);
    expect(a.spanId).not.toBe(b.spanId);
  });
});

describe('shouldCollect', () => {
  it('is true when a test fails and was expected to pass', () => {
    expect(shouldCollect('failed', 'passed')).toBe(true);
  });

  it('is true when a test times out and was expected to pass', () => {
    expect(shouldCollect('timedOut', 'passed')).toBe(true);
  });

  it('is false for an expected failure (test.fail)', () => {
    expect(shouldCollect('failed', 'failed')).toBe(false);
  });

  it('is false when a test is skipped', () => {
    expect(shouldCollect('skipped', 'passed')).toBe(false);
  });

  it('is false when a test passes', () => {
    expect(shouldCollect('passed', 'passed')).toBe(false);
  });

  it('is true when a test.fail() test times out instead of failing', () => {
    expect(shouldCollect('timedOut', 'failed')).toBe(true);
  });
});

describe('collectJaegerSpans', () => {
  it('returns JAEGER_QUERY_URL unset without calling fetchFn when queryUrl is missing', async () => {
    const fetchFn = vi.fn();
    const result = await collectJaegerSpans('abc123', {
      fetchFn: fetchFn as unknown as typeof fetch,
      sleepFn: async () => undefined,
    });
    expect(result).toEqual({ok: false, reason: 'JAEGER_QUERY_URL unset'});
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('retries at a fixed cadence until the deadline then reports unreachable', async () => {
    vi.useFakeTimers();
    try {
      const fetchFn = vi.fn().mockRejectedValue(new Error('offline'));
      // Fake timers make Date.now() advance only via vi.runAllTimersAsync(),
      // so attempts land at exactly 0/20/40/60ms elapsed against a 50ms
      // deadline regardless of host load: 4 attempts by arithmetic.
      const resultPromise = collectJaegerSpans('abc123', {
        queryUrl: 'http://jaeger.example',
        fetchFn: fetchFn as unknown as typeof fetch,
        deadlineMs: 50,
        retryDelayMs: 20,
      });
      await vi.runAllTimersAsync();
      const result = await resultPromise;
      expect(result.ok).toBe(false);
      if (result.ok === false) {
        expect(result.reason).toMatch(/^unreachable: offline$/);
      }
      expect(fetchFn.mock.calls.length).toBe(4);
    } finally {
      vi.useRealTimers();
    }
  });

  it('reports no spans when every attempt returns an empty trace', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({data: []}),
    });
    const sleepFn = vi.fn().mockResolvedValue(undefined);
    const result = await collectJaegerSpans('abc123', {
      queryUrl: 'http://jaeger.example',
      fetchFn: fetchFn as unknown as typeof fetch,
      sleepFn,
      deadlineMs: 30,
      retryDelayMs: 1,
    });
    expect(result).toEqual({
      ok: false,
      reason:
        'no spans for trace abc123 (likely cause: requests made without the per-test traceparent header, e.g. a spec-local request context, are not attributable)',
    });
  });

  it('reports malformed response when JSON parsing fails', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => 'not json',
    });
    const sleepFn = vi.fn().mockResolvedValue(undefined);
    const result = await collectJaegerSpans('abc123', {
      queryUrl: 'http://jaeger.example',
      fetchFn: fetchFn as unknown as typeof fetch,
      sleepFn,
      deadlineMs: 30,
      retryDelayMs: 1,
    });
    expect(result.ok).toBe(false);
    if (result.ok === false) {
      expect(result.reason).toMatch(/^malformed response:/);
    }
  });

  it('reports the HTTP status when Jaeger responds with an error', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      text: async () => '<html>bad gateway</html>',
    });
    const sleepFn = vi.fn().mockResolvedValue(undefined);
    const result = await collectJaegerSpans('abc123', {
      queryUrl: 'http://jaeger.example',
      fetchFn: fetchFn as unknown as typeof fetch,
      sleepFn,
      deadlineMs: 30,
      retryDelayMs: 1,
    });
    expect(result).toEqual({
      ok: false,
      reason: 'jaeger query failed: 502 Bad Gateway',
    });
  });

  it('succeeds once a retry returns spans', async () => {
    const body = JSON.stringify({data: [{spans: [{spanId: '1'}]}]});
    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({data: []}),
      })
      .mockResolvedValueOnce({ok: true, text: async () => body});
    const sleepFn = vi.fn().mockResolvedValue(undefined);
    const result = await collectJaegerSpans('abc123', {
      queryUrl: 'http://jaeger.example',
      fetchFn: fetchFn as unknown as typeof fetch,
      sleepFn,
      deadlineMs: 1000,
      retryDelayMs: 1,
    });
    expect(result).toEqual({ok: true, body});
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });
});

describe('attachFailureArtifacts', () => {
  it('attaches not-collected.txt when Jaeger is unreachable', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    const previousJaegerQueryUrl = process.env.JAEGER_QUERY_URL;
    process.env.JAEGER_QUERY_URL = 'http://jaeger.example';

    try {
      const attached: string[] = [];
      const annotations: {type: string; description?: string}[] = [];
      const testInfo = {
        outputPath: (name: string) => `/tmp/${name}`,
        attach: vi.fn(async (name: string) => {
          attached.push(name);
        }),
        annotations: {push: vi.fn((a) => annotations.push(a))},
      } as unknown as TestInfo;

      const runPromise = attachFailureArtifacts(testInfo, newTraceContext());
      await vi.runAllTimersAsync();
      await runPromise;

      expect(attached).toEqual(['not-collected.txt']);

      const notCollectedCall = vi
        .mocked(writeFile)
        .mock.calls.find(([path]) => path === '/tmp/not-collected.txt');
      const body = notCollectedCall?.[1] as string;
      expect(body).toContain('server-spans.json: not collected: unreachable');

      expect(annotations).toEqual([
        {
          type: 'failure-artifacts',
          description:
            'attached=[not-collected.txt] not-collected=[server-spans.json]',
        },
      ]);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
      if (previousJaegerQueryUrl === undefined) {
        delete process.env.JAEGER_QUERY_URL;
      } else {
        process.env.JAEGER_QUERY_URL = previousJaegerQueryUrl;
      }
    }
  });

  it('attaches server-spans.json when Jaeger returns spans', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (String(url).includes('/api/traces/')) {
          return {
            ok: true,
            text: async () =>
              JSON.stringify({data: [{spans: [{spanId: '1'}]}]}),
          } as Response;
        }
        throw new Error('offline');
      }),
    );
    const previousJaegerQueryUrl = process.env.JAEGER_QUERY_URL;
    process.env.JAEGER_QUERY_URL = 'http://jaeger.example';

    try {
      const attached: string[] = [];
      const annotations: {type: string; description?: string}[] = [];
      const testInfo = {
        outputPath: (name: string) => `/tmp/${name}`,
        attach: vi.fn(async (name: string) => {
          attached.push(name);
        }),
        annotations: {push: vi.fn((a) => annotations.push(a))},
      } as unknown as TestInfo;

      const runPromise = attachFailureArtifacts(testInfo, newTraceContext());
      await vi.runAllTimersAsync();
      await runPromise;

      expect(attached).toEqual(['server-spans.json']);

      const spansCall = vi
        .mocked(writeFile)
        .mock.calls.find(([path]) => path === '/tmp/server-spans.json');
      expect(spansCall?.[1]).toContain('spanId');

      expect(annotations).toEqual([
        {
          type: 'failure-artifacts',
          description: 'attached=[server-spans.json] not-collected=[]',
        },
      ]);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
      if (previousJaegerQueryUrl === undefined) {
        delete process.env.JAEGER_QUERY_URL;
      } else {
        process.env.JAEGER_QUERY_URL = previousJaegerQueryUrl;
      }
    }
  });

  it('never throws even when testInfo.attach itself rejects', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify({data: [{spans: [{spanId: '1'}]}]}),
      }),
    );
    const previousJaegerQueryUrl = process.env.JAEGER_QUERY_URL;
    process.env.JAEGER_QUERY_URL = 'http://jaeger.example';

    try {
      const annotations: {type: string; description?: string}[] = [];
      const testInfo = {
        outputPath: (name: string) => `/tmp/${name}`,
        attach: vi.fn().mockRejectedValue(new Error('disk full')),
        annotations: {push: vi.fn((a) => annotations.push(a))},
      } as unknown as TestInfo;

      const runPromise = attachFailureArtifacts(testInfo, newTraceContext());
      await vi.runAllTimersAsync();
      await expect(runPromise).resolves.toBeUndefined();

      expect(annotations).toEqual([
        {
          type: 'failure-artifacts',
          description: 'failed: disk full',
        },
      ]);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
      if (previousJaegerQueryUrl === undefined) {
        delete process.env.JAEGER_QUERY_URL;
      } else {
        process.env.JAEGER_QUERY_URL = previousJaegerQueryUrl;
      }
    }
  });
});
