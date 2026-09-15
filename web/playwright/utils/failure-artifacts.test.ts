// @vitest-environment node

import {describe, expect, it, vi} from 'vitest';
import type {TestInfo} from '@playwright/test';
import {writeFile} from 'fs/promises';
import {mkdtempSync, rmSync, writeFileSync} from 'fs';
import {tmpdir} from 'os';
import {join} from 'path';
import {
  attachFailureArtifacts,
  capTail,
  collectJaegerSpans,
  interleaveTimestampedLines,
  logWindow,
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

describe('logWindow', () => {
  it('pads both sides of the window and returns ISO-8601 strings', () => {
    const startedAt = new Date('2026-01-01T00:00:05.000Z');
    const endedAt = new Date('2026-01-01T00:00:10.000Z');
    const {since, until} = logWindow(startedAt, endedAt, 2000);
    expect(since).toBe('2026-01-01T00:00:03.000Z');
    expect(until).toBe('2026-01-01T00:00:12.000Z');
  });

  it('defaults the pad to 2000ms', () => {
    const startedAt = new Date('2026-01-01T00:00:05.000Z');
    const endedAt = new Date('2026-01-01T00:00:10.000Z');
    const {since, until} = logWindow(startedAt, endedAt);
    expect(since).toBe('2026-01-01T00:00:03.000Z');
    expect(until).toBe('2026-01-01T00:00:12.000Z');
  });
});

describe('capTail', () => {
  it('returns text unchanged when at or under the cap', () => {
    const text = 'hello world';
    expect(capTail(text, Buffer.byteLength(text))).toBe(text);
    expect(capTail(text, Buffer.byteLength(text) + 10)).toBe(text);
  });

  it('truncates and preserves the exact tail when over the cap', () => {
    const text = '0123456789';
    const result = capTail(text, 4);
    expect(result).toBe('[truncated: kept last 4 of 10 bytes]\n6789');
  });

  it('does not throw when the cap cuts a multibyte UTF-8 character', () => {
    // '€' is 3 bytes in UTF-8; capping at a byte offset that splits it must
    // not throw, even though the decoded tail may contain a replacement char.
    const text = 'ab€cd';
    expect(() => capTail(text, 3)).not.toThrow();
  });
});

describe('interleaveTimestampedLines', () => {
  it('merges two --timestamps-prefixed streams into chronological order', () => {
    const stdout = ['2026-01-01T00:00:00.000000000Z out1'].join('\n');
    const stderr = [
      '2026-01-01T00:00:01.000000000Z err1',
      '2026-01-01T00:00:02.000000000Z err2',
    ].join('\n');
    expect(interleaveTimestampedLines(stdout, stderr)).toBe(
      [
        '2026-01-01T00:00:00.000000000Z out1',
        '2026-01-01T00:00:01.000000000Z err1',
        '2026-01-01T00:00:02.000000000Z err2',
      ].join('\n'),
    );
  });

  it('interleaves a stderr line between two stdout lines, unlike concatenation', () => {
    const stdout = [
      '2026-01-01T00:00:00.000000000Z out1',
      '2026-01-01T00:00:02.000000000Z out2',
    ].join('\n');
    const stderr = ['2026-01-01T00:00:01.000000000Z err1'].join('\n');
    expect(interleaveTimestampedLines(stdout, stderr)).toBe(
      [
        '2026-01-01T00:00:00.000000000Z out1',
        '2026-01-01T00:00:01.000000000Z err1',
        '2026-01-01T00:00:02.000000000Z out2',
      ].join('\n'),
    );
  });

  it('drops empty lines from either stream', () => {
    expect(interleaveTimestampedLines('', '')).toBe('');
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

  it('succeeds once a retry returns spans', async () => {
    const body = JSON.stringify({data: [{spans: [{spanId: '1'}]}]});
    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce({text: async () => JSON.stringify({data: []})})
      .mockResolvedValueOnce({text: async () => body});
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
  it('attaches not-collected.txt when every collector fails', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    process.env.QUAY_LOG_CMD = 'quay-test-cmd-that-does-not-exist';

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

      const runPromise = attachFailureArtifacts(
        testInfo,
        newTraceContext(),
        new Date(),
      );
      await vi.runAllTimersAsync();
      await runPromise;

      expect(attached).toEqual(['not-collected.txt']);

      const notCollectedCall = vi
        .mocked(writeFile)
        .mock.calls.find(([path]) => path === '/tmp/not-collected.txt');
      const body = notCollectedCall?.[1] as string;
      expect(body).toContain('server-spans.json');
      expect(body).toContain('quay-logs.txt');

      expect(annotations).toEqual([
        {
          type: 'failure-artifacts',
          description:
            'attached=[not-collected.txt] not-collected=[server-spans.json,quay-logs.txt]',
        },
      ]);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
      delete process.env.QUAY_LOG_CMD;
    }
  });

  it('attaches server-spans.json when Jaeger returns spans', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (String(url).includes('/api/traces/')) {
          return {
            text: async () =>
              JSON.stringify({data: [{spans: [{spanId: '1'}]}]}),
          } as Response;
        }
        throw new Error('offline');
      }),
    );
    const previousJaegerQueryUrl = process.env.JAEGER_QUERY_URL;
    const previousQuayLogCmd = process.env.QUAY_LOG_CMD;
    process.env.JAEGER_QUERY_URL = 'http://jaeger.example';
    process.env.QUAY_LOG_CMD = 'quay-test-cmd-that-does-not-exist';

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

      const runPromise = attachFailureArtifacts(
        testInfo,
        newTraceContext(),
        new Date(),
      );
      await vi.runAllTimersAsync();
      await runPromise;

      expect(attached).toEqual(['server-spans.json', 'not-collected.txt']);

      const spansCall = vi
        .mocked(writeFile)
        .mock.calls.find(([path]) => path === '/tmp/server-spans.json');
      expect(spansCall?.[1]).toContain('spanId');

      expect(annotations).toEqual([
        {
          type: 'failure-artifacts',
          description:
            'attached=[server-spans.json,not-collected.txt] not-collected=[quay-logs.txt]',
        },
      ]);
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
      if (previousQuayLogCmd === undefined) {
        delete process.env.QUAY_LOG_CMD;
      } else {
        process.env.QUAY_LOG_CMD = previousQuayLogCmd;
      }
      if (previousJaegerQueryUrl === undefined) {
        delete process.env.JAEGER_QUERY_URL;
      } else {
        process.env.JAEGER_QUERY_URL = previousJaegerQueryUrl;
      }
    }
  });

  it('streams a container log far larger than the old 8 MiB buffer without crashing', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'quay-log-emitter-'));
    const scriptPath = join(dir, 'emit.sh');
    const totalLines = 150000;
    const lastLine = String(totalLines).padStart(6, '0');
    const script = [
      '#!/bin/sh',
      'i=1',
      `while [ "$i" -le ${totalLines} ]; do`,
      '  printf \'2026-01-01T00:00:00.%06dZ line-%06d xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\\n\' "$i" "$i"',
      '  i=$((i + 1))',
      'done',
      '',
    ].join('\n');
    writeFileSync(scriptPath, script, {mode: 0o755});

    const previousQuayLogCmd = process.env.QUAY_LOG_CMD;
    process.env.QUAY_LOG_CMD = scriptPath;

    try {
      const annotations: {type: string; description?: string}[] = [];
      const testInfo = {
        outputPath: (name: string) => `/tmp/${name}`,
        attach: vi.fn(async () => undefined),
        annotations: {push: vi.fn((a) => annotations.push(a))},
      } as unknown as TestInfo;

      await attachFailureArtifacts(testInfo, newTraceContext(), new Date());

      expect(annotations[0].description).toMatch(
        /attached=\[[^\]]*quay-logs\.txt/,
      );
      expect(annotations[0].description).not.toMatch(
        /not-collected=\[[^\]]*quay-logs\.txt/,
      );

      const logsCall = vi
        .mocked(writeFile)
        .mock.calls.find(([path]) => path === '/tmp/quay-logs.txt');
      expect(logsCall).toBeDefined();
      const body = logsCall?.[1] as string;

      expect(body.length).toBeGreaterThan(0);
      expect(body.length).toBeLessThan(1024 * 1024 + 200);
      expect(body).not.toContain('line-000001 ');
      expect(body).toContain(`line-${lastLine} `);
    } finally {
      if (previousQuayLogCmd === undefined) {
        delete process.env.QUAY_LOG_CMD;
      } else {
        process.env.QUAY_LOG_CMD = previousQuayLogCmd;
      }
      rmSync(dir, {recursive: true, force: true});
    }
  }, 20000);

  it('lists quay-logs.txt as attached, not not-collected, on success', async () => {
    const previousQuayLogCmd = process.env.QUAY_LOG_CMD;
    process.env.QUAY_LOG_CMD = '/bin/echo';

    try {
      const annotations: {type: string; description?: string}[] = [];
      const testInfo = {
        outputPath: (name: string) => `/tmp/${name}`,
        attach: vi.fn(async () => undefined),
        annotations: {push: vi.fn((a) => annotations.push(a))},
      } as unknown as TestInfo;

      await attachFailureArtifacts(testInfo, newTraceContext(), new Date());

      expect(annotations).toEqual([
        {
          type: 'failure-artifacts',
          description:
            'attached=[quay-logs.txt,not-collected.txt] not-collected=[server-spans.json]',
        },
      ]);
    } finally {
      if (previousQuayLogCmd === undefined) {
        delete process.env.QUAY_LOG_CMD;
      } else {
        process.env.QUAY_LOG_CMD = previousQuayLogCmd;
      }
    }
  });
});
