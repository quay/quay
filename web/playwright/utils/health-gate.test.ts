// @vitest-environment node

import {describe, expect, it} from 'vitest';
import {FINALIZE_OPERATION, classifyTraces} from './health-gate';

function span(
  operationName: string,
  status: number,
  durationUs: number,
  opts: {traceID?: string; spanID?: string; parent?: string} = {},
) {
  return {
    traceID: opts.traceID ?? 'trace-1',
    spanID: opts.spanID ?? 'root',
    operationName,
    duration: durationUs,
    references: opts.parent ? [{refType: 'CHILD_OF', spanID: opts.parent}] : [],
    tags: [{key: 'http.status_code', type: 'int64', value: status}],
  };
}

const body = (...spans: ReturnType<typeof span>[]) => ({
  data: spans.map((s) => ({spans: [s]})),
});

describe('classifyTraces', () => {
  it('flags a 503 on a blob finalize PUT', () => {
    const result = classifyTraces(
      body(span(FINALIZE_OPERATION, 503, 3_200_000, {traceID: 'abc'})),
    );

    expect(result.v2Errors).toEqual([
      {route: FINALIZE_OPERATION, status: 503, count: 1, traceId: 'abc'},
    ]);
  });

  it('ignores a 503 outside /v2', () => {
    const result = classifyTraces(body(span('GET /health/instance', 503, 1)));

    expect(result.v2Errors).toEqual([]);
  });

  it('counts a 4.0s finalize PUT in the lock band only', () => {
    const result = classifyTraces(
      body(
        span(FINALIZE_OPERATION, 201, 4_000_000),
        span(FINALIZE_OPERATION, 201, 100_000),
      ),
    );

    expect(result.v2Errors).toEqual([]);
    expect(result.lockBand).toEqual({
      finalizePuts: 2,
      inBand: 1,
      maxUs: 4_000_000,
      p99Us: 4_000_000,
    });
  });

  it('does not count a nested 5xx span', () => {
    const result = classifyTraces({
      data: [
        {
          spans: [
            span(FINALIZE_OPERATION, 503, 3_200_000),
            span(FINALIZE_OPERATION, 503, 3_100_000, {
              spanID: 'child',
              parent: 'root',
            }),
          ],
        },
      ],
    });

    expect(result.v2Errors).toHaveLength(1);
    expect(result.v2Errors[0].count).toBe(1);
  });

  it('flags a 5xx whose propagated parent is not in the trace', () => {
    const result = classifyTraces(
      body(span('GET /v2/auth', 500, 1, {parent: 'test-span'})),
    );

    expect(result.v2Errors).toEqual([
      {route: 'GET /v2/auth', status: 500, count: 1, traceId: 'trace-1'},
    ]);
  });
});
