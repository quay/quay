import {readFile} from 'fs/promises';
import {expect, test} from '@playwright/test';
import {
  FINALIZE_OPERATION,
  JaegerTracesResponse,
  LockBand,
  TraceQuery,
  V2ErrorGroup,
  classifyTraces,
  fetchTraces,
  suiteStartFile,
} from '../../utils/health-gate';

// Quay's BatchSpanProcessor exports every 5s; wait two cycles so the last
// tests' spans are queryable.
const SPAN_EXPORT_LAG_MS = 10_000;
const ERROR_LIMIT = 1000;
const FINALIZE_LIMIT = 5000;

const secs = (us: number) => `${(us / 1e6).toFixed(2)}s`;

function formatGroup(g: V2ErrorGroup): string {
  return `${g.count}x ${g.status} ${g.route} (trace ${g.traceId})`;
}

function formatLockBand(b: LockBand): string {
  return `${b.inBand} of ${b.finalizePuts} finalize PUTs >= 3s; max ${secs(
    b.maxUs,
  )}; p99 ${secs(b.p99Us)}`;
}

test.describe('health', {tag: ['@health']}, () => {
  test('no /v2 5xx in the suite Jaeger traces', async () => {
    const queryUrl = process.env.JAEGER_QUERY_URL;
    if (!queryUrl) {
      test.skip(true, 'JAEGER_QUERY_URL unset');
      return;
    }
    const testInfo = test.info();

    const startUs = Number(
      await readFile(suiteStartFile(testInfo.project.outputDir), 'utf8'),
    );
    await new Promise((resolve) => setTimeout(resolve, SPAN_EXPORT_LAG_MS));
    const endUs = Date.now() * 1000;

    const errorQuery: TraceQuery = {
      startUs,
      endUs,
      limit: ERROR_LIMIT,
      // The Flask instrumentation marks every 5xx server span error=true.
      filter: {tags: JSON.stringify({error: 'true'})},
    };
    const finalizeQuery: TraceQuery = {
      startUs,
      endUs,
      limit: FINALIZE_LIMIT,
      filter: {operation: FINALIZE_OPERATION},
    };
    let errors: JaegerTracesResponse;
    let finalizes: JaegerTracesResponse;
    try {
      [errors, finalizes] = await Promise.all([
        fetchTraces(queryUrl, errorQuery),
        fetchTraces(queryUrl, finalizeQuery),
      ]);
    } catch (err) {
      test.skip(
        true,
        `Jaeger query failed: ${err instanceof Error ? err.message : err}`,
      );
      return;
    }

    const lockBand = classifyTraces(finalizes).lockBand;
    if (lockBand.inBand > 0) {
      const description = formatLockBand(lockBand);
      testInfo.annotations.push({type: 'lock-band', description});
      console.log(`[health-gate] lock-band: ${description}`);
    }

    const window = `${new Date(startUs / 1000).toISOString()}..${new Date(
      endUs / 1000,
    ).toISOString()}`;
    expect(
      classifyTraces(errors).v2Errors.map(formatGroup),
      `/v2 entry spans with HTTP 5xx in ${window}`,
    ).toEqual([]);
  });
});
