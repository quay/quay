// @vitest-environment node

import {describe, expect, it} from 'vitest';
import {isPushRetryable} from './container';

describe('isPushRetryable', () => {
  it('returns false for a quota-exceeded error from Quay', () => {
    const err = new Error(
      'skopeo copy failed with exit code 1: DENIED: Quota has been exceeded on namespace; map[]',
    );
    expect(isPushRetryable(err)).toBe(false);
  });

  it('returns false when the message contains only the key phrase', () => {
    const err = new Error('Quota has been exceeded');
    expect(isPushRetryable(err)).toBe(false);
  });

  it('returns true for a transient network error', () => {
    const err = new Error('ECONNREFUSED');
    expect(isPushRetryable(err)).toBe(true);
  });

  it('returns true for a repository-not-found error', () => {
    const err = new Error(
      'skopeo copy failed with exit code 1: DENIED: Repository not found',
    );
    expect(isPushRetryable(err)).toBe(true);
  });

  it('returns true for a non-Error thrown value', () => {
    expect(isPushRetryable('string error')).toBe(true);
    expect(isPushRetryable(42)).toBe(true);
    expect(isPushRetryable(null)).toBe(true);
    expect(isPushRetryable(undefined)).toBe(true);
  });

  it('returns true for an Error whose message does not mention quota', () => {
    const err = new Error('timeout waiting for blob upload');
    expect(isPushRetryable(err)).toBe(true);
  });
});
