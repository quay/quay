/**
 * Security scanner utilities for Playwright e2e tests.
 *
 * Provides helpers for waiting on async Clair security scans to complete.
 */

import {ApiClient} from './api';

/**
 * Wait for Clair to finish scanning a manifest.
 * Polls the security endpoint until status is no longer 'queued'.
 */
export async function waitForSecurityScan(
  client: ApiClient,
  namespace: string,
  repo: string,
  manifestDigest: string,
  timeoutMs = 60000,
  pollIntervalMs = 3000,
): Promise<{status: string; data: unknown}> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await client.getManifestSecurity(
      namespace,
      repo,
      manifestDigest,
    );
    if (result.status !== 'queued') {
      return result;
    }
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }
  throw new Error(
    `Security scan for ${namespace}/${repo}@${manifestDigest} did not complete within ${timeoutMs}ms`,
  );
}
