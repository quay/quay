/**
 * Suite health gate over the run's own Jaeger traces: /v2 server errors
 * (fail the run) and blob-finalize PUTs in the 3s lock band (warn only).
 */

import path from 'path';

export const FINALIZE_OPERATION =
  'PUT /v2/<repopath:repository>/blobs/uploads/<upload_uuid>';
// BLOB_DELETE_<digest> lock wait bound in the finalize PUT.
const LOCK_BAND_MIN_US = 3_000_000;

const V2_ROUTE = /^[A-Z]+ \/v2(\/|$)/;
const FINALIZE_PUT = /^PUT \/v2\/.+\/blobs\/uploads\/.+/;

interface JaegerTag {
  key: string;
  value: unknown;
}

interface JaegerSpan {
  traceID: string;
  spanID: string;
  operationName: string;
  duration: number;
  references?: {spanID: string}[] | null;
  tags?: JaegerTag[] | null;
}

export interface JaegerTracesResponse {
  data?: {spans?: JaegerSpan[] | null}[] | null;
}

export interface V2ErrorGroup {
  route: string;
  status: number;
  count: number;
  traceId: string;
}

export interface LockBand {
  finalizePuts: number;
  inBand: number;
  maxUs: number;
  p99Us: number;
}

interface Classification {
  v2Errors: V2ErrorGroup[];
  lockBand: LockBand;
}

function statusCode(span: JaegerSpan): number {
  const tag = span.tags?.find((t) => t.key === 'http.status_code');
  return Number(tag?.value ?? 0);
}

/**
 * Classifies entry spans of a /api/traces body: spans with no parent in their
 * own trace. Suite requests carry the test's traceparent, so their server span
 * references a parent that is never exported.
 */
export function classifyTraces(body: JaegerTracesResponse): Classification {
  const roots = (body.data ?? []).flatMap((trace) => {
    const spans = trace.spans ?? [];
    const ids = new Set(spans.map((span) => span.spanID));
    return spans.filter(
      (span) => !span.references?.some((ref) => ids.has(ref.spanID)),
    );
  });

  const groups = new Map<string, V2ErrorGroup>();
  for (const span of roots) {
    const status = statusCode(span);
    if (status < 500 || !V2_ROUTE.test(span.operationName)) continue;
    const key = `${span.operationName} ${status}`;
    const group = groups.get(key);
    if (group) {
      group.count++;
    } else {
      groups.set(key, {
        route: span.operationName,
        status,
        count: 1,
        traceId: span.traceID,
      });
    }
  }

  const durations = roots
    .filter((span) => FINALIZE_PUT.test(span.operationName))
    .map((span) => span.duration)
    .sort((a, b) => a - b);

  return {
    v2Errors: Array.from(groups.values()).sort((a, b) => b.count - a.count),
    lockBand: {
      finalizePuts: durations.length,
      inBand: durations.filter((d) => d >= LOCK_BAND_MIN_US).length,
      maxUs: durations[durations.length - 1] ?? 0,
      // nearest-rank p99
      p99Us: durations[Math.ceil(durations.length * 0.99) - 1] ?? 0,
    },
  };
}

/** Where the setup project records the suite start for the gate to read. */
export function suiteStartFile(outputDir: string): string {
  return path.join(outputDir, 'health-gate-suite-start-us');
}

export interface TraceQuery {
  startUs: number;
  endUs: number;
  limit: number;
  // Always filtered: an unfiltered query over a whole run can OOM the
  // in-memory Jaeger.
  filter: {tags: string} | {operation: string};
}

/** GETs /api/traces for service quay; throws on any transport or HTTP error. */
export async function fetchTraces(
  queryUrl: string,
  query: TraceQuery,
): Promise<JaegerTracesResponse> {
  const params = new URLSearchParams({
    service: 'quay',
    start: String(query.startUs),
    end: String(query.endUs),
    limit: String(query.limit),
    ...query.filter,
  });
  const res = await fetch(`${queryUrl}/api/traces?${params}`, {
    signal: AbortSignal.timeout(30_000),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as JaegerTracesResponse;
}
