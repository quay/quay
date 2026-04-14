/**
 * Test utilities for Playwright tests.
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
