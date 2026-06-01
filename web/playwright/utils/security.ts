/**
 * Security scanner utilities for Playwright e2e tests.
 *
 * Provides helpers for waiting on async Clair security scans to complete.
 */

import {ApiClient} from './api';

export type ScanTerminalStatus =
  | 'scanned'
  | 'failed'
  | 'unsupported'
  | 'manifest_layer_too_large';

export interface ScanResult {
  ok: boolean;
  status: ScanTerminalStatus | 'timeout';
  data?: unknown;
}

const TERMINAL_STATUSES = new Set<string>([
  'scanned',
  'failed',
  'unsupported',
  'manifest_layer_too_large',
]);

/**
 * Wait for Clair to finish scanning a manifest.
 *
 * Returns a ScanResult indicating whether the scan succeeded. Callers
 * should check `result.ok` and skip tests when the scan did not produce
 * vulnerability data.
 *
 * Retries on HTTP 404 (manifest not yet visible), 500 (internal scanner
 * error), and 520 (downstream_issue / transient Clair failure).
 */
export async function waitForSecurityScan(
  client: ApiClient,
  namespace: string,
  repo: string,
  manifestDigest: string,
  timeoutMs = 60000,
  pollIntervalMs = 3000,
): Promise<ScanResult> {
  const RETRIABLE_HTTP_RE = /:\s*(404|500|520)\s*-/;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const result = await client.getManifestSecurity(
        namespace,
        repo,
        manifestDigest,
      );

      if (TERMINAL_STATUSES.has(result.status)) {
        return {
          ok: result.status === 'scanned',
          status: result.status as ScanTerminalStatus,
          data: result.data,
        };
      }
    } catch (e: unknown) {
      if (e instanceof Error && RETRIABLE_HTTP_RE.test(e.message)) {
        // Transient — keep polling
      } else {
        throw e;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  return {ok: false, status: 'timeout'};
}
