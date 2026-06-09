/**
 * Test utilities for Playwright tests.
 */

/**
 * Generate a unique name for test resources.
 * Uses timestamp + random suffix to avoid collisions across parallel workers.
 */
export function uniqueName(prefix: string): string {
  const bytes = new Uint8Array(4);
  crypto.getRandomValues(bytes);
  const rand = Array.from(bytes, (b) => b.toString(36).padStart(2, '0'))
    .join('')
    .substring(0, 8);
  return `${prefix}-${Date.now()}-${rand}`;
}
