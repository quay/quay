/**
 * Per-test W3C trace propagation and on-failure diagnostic attachments
 * (Jaeger spans for a failed test).
 */

import {randomBytes} from 'crypto';
import {writeFile} from 'fs/promises';
import {TestInfo, TestStatus} from '@playwright/test';

export interface TraceContext {
  traceId: string;
  spanId: string;
  traceparent: string;
}

/** Generates a fresh W3C trace id (32 hex chars) and span id (16 hex chars). */
export function newTraceContext(): TraceContext {
  const traceId = randomBytes(16).toString('hex');
  const spanId = randomBytes(8).toString('hex');
  return {
    traceId,
    spanId,
    traceparent: `00-${traceId}-${spanId}-01`,
  };
}

/** True only when the test actually failed (not skipped, not an expected failure). */
export function shouldCollect(
  status: TestStatus | undefined,
  expectedStatus: TestStatus,
): boolean {
  return (
    (status === 'failed' || status === 'timedOut') && status !== expectedStatus
  );
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export interface CollectJaegerSpansOptions {
  queryUrl?: string;
  fetchFn?: typeof fetch;
  sleepFn?: (ms: number) => Promise<void>;
  // Quay's BatchSpanProcessor exports every 5s. 12s gives roughly two full
  // export cycles of margin at the default attempt/retry timings below.
  deadlineMs?: number;
  attemptTimeoutMs?: number;
  retryDelayMs?: number;
}

export type CollectJaegerSpansResult =
  | {ok: true; body: string}
  | {ok: false; reason: string};

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/** Fetches Jaeger spans for a trace, retrying until deadlineMs elapses. Never throws. */
export async function collectJaegerSpans(
  traceId: string,
  opts: CollectJaegerSpansOptions = {},
): Promise<CollectJaegerSpansResult> {
  const {
    queryUrl,
    fetchFn = fetch,
    sleepFn = sleep,
    deadlineMs = 12000,
    attemptTimeoutMs = 2000,
    retryDelayMs = 1000,
  } = opts;

  if (!queryUrl) {
    return {ok: false, reason: 'JAEGER_QUERY_URL unset'};
  }

  const url = `${queryUrl}/api/traces/${traceId}`;
  const deadline = Date.now() + deadlineMs;
  const noSpansReason = `no spans for trace ${traceId} (likely cause: requests made without the per-test traceparent header, e.g. a spec-local request context, are not attributable)`;
  let lastReason = noSpansReason;

  for (;;) {
    try {
      const res = await fetchFn(url, {
        signal: AbortSignal.timeout(attemptTimeoutMs),
      });
      if (!res.ok) {
        lastReason = `jaeger query failed: ${res.status} ${res.statusText}`;
      } else {
        const body = await res.text();
        try {
          const parsed = JSON.parse(body);
          const spans = parsed?.data?.[0]?.spans;
          if (Array.isArray(spans) && spans.length > 0) {
            return {ok: true, body};
          }
          lastReason = noSpansReason;
        } catch (err) {
          lastReason = `malformed response: ${errMessage(err)}`;
        }
      }
    } catch (err) {
      lastReason = `unreachable: ${errMessage(err)}`;
    }

    if (Date.now() >= deadline) {
      return {ok: false, reason: lastReason};
    }
    await sleepFn(retryDelayMs);
  }
}

async function writeAndAttach(
  testInfo: TestInfo,
  name: string,
  body: string,
  contentType: string,
): Promise<void> {
  const path = testInfo.outputPath(name);
  await writeFile(path, body);
  await testInfo.attach(name, {path, contentType});
}

/**
 * Best-effort attachment for a failed test: Jaeger spans for this test's
 * trace id. Never throws -- attachment failures must not mask the original
 * test failure, and a degraded fetch becomes a line in not-collected.txt
 * instead.
 */
export async function attachFailureArtifacts(
  testInfo: TestInfo,
  trace: TraceContext,
): Promise<void> {
  try {
    const spansResult = await collectJaegerSpans(trace.traceId, {
      queryUrl: process.env.JAEGER_QUERY_URL,
    });

    const attached: string[] = [];

    if (spansResult.ok === true) {
      await writeAndAttach(
        testInfo,
        'server-spans.json',
        spansResult.body,
        'application/json',
      );
      attached.push('server-spans.json');
    } else {
      try {
        const body = `server-spans.json: not collected: ${spansResult.reason}\n`;
        await writeAndAttach(testInfo, 'not-collected.txt', body, 'text/plain');
        attached.push('not-collected.txt');
      } catch {
        // best-effort; nothing to fall back to
      }
    }

    testInfo.annotations.push({
      type: 'failure-artifacts',
      description: `attached=[${attached.join(',')}] not-collected=[${
        spansResult.ok === true ? '' : 'server-spans.json'
      }]`,
    });
  } catch (err) {
    // best-effort diagnostics must never affect the test outcome, but still
    // leave one annotation so a debugger knows the machinery ran and failed
    testInfo.annotations.push({
      type: 'failure-artifacts',
      description: `failed: ${errMessage(err)}`,
    });
  }
}
