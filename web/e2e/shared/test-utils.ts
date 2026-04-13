/**
 * Shared test utilities used by both UI (Playwright) and API test suites.
 */

/**
 * Generate a unique name for test resources.
 * Uses timestamp + random suffix to avoid collisions across parallel workers.
 */
export function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random()
    .toString(36)
    .substring(2, 8)}`;
}
